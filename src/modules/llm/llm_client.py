"""
大语言模型客户端
支持多种LLM API：OpenAI, Anthropic, 本地模型等
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Union
from loguru import logger
import httpx
import time

from ...utils.config import LLMConfig


class LLMClient:
    """大语言模型客户端"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        
        # 请求统计
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "avg_latency": 0.0,
            "errors": 0
        }
        
        logger.info(f"LLM客户端初始化，提供商: {config.text_provider}")

    async def initialize(self):
        """初始化LLM客户端"""
        if self._initialized:
            return
            
        try:
            # 创建HTTP客户端
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=5)
            )
            
            # 验证API密钥
            if not await self._test_connection():
                logger.warning("LLM API连接测试失败，但继续初始化")
            
            self._initialized = True
            logger.info(f"LLM客户端初始化完成: {self.config.text_provider}")
            
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {e}")
            raise

    async def _test_connection(self) -> bool:
        """测试API连接"""
        try:
            # 发送简单的测试请求
            test_messages = [{"role": "user", "content": "Hi"}]
            response = await self.chat_completion(test_messages, max_tokens=5)
            return bool(response)
            
        except Exception as e:
            logger.error(f"API连接测试失败: {e}")
            return False

    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            max_tokens: int = 1000,
                            temperature: float = 0.7,
                            **kwargs) -> str:
        """
        发送聊天完成请求
        
        Args:
            messages: 对话消息列表
            max_tokens: 最大令牌数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            模型回复的文本
        """
        if not self._initialized or not self._client:
            logger.error("LLM客户端未初始化")
            return ""
            
        start_time = time.time()
        
        try:
            if self.config.text_provider == "openai":
                response = await self._openai_request(messages, max_tokens, temperature, **kwargs)
            elif self.config.text_provider == "anthropic":
                response = await self._anthropic_request(messages, max_tokens, temperature, **kwargs)
            elif self.config.text_provider == "local" or self.config.text_provider == "ollama":
                response = await self._local_request(messages, max_tokens, temperature, **kwargs)
            else:
                logger.error(f"不支持的LLM提供商: {self.config.text_provider}")
                return ""
            
            # 更新统计信息
            latency = time.time() - start_time
            self._update_stats(latency, len(response))
            
            return response
            
        except Exception as e:
            logger.error(f"LLM请求失败: {e}")
            self.stats["errors"] += 1
            return ""

    async def _openai_request(self, messages: List[Dict[str, str]], 
                            max_tokens: int, temperature: float, **kwargs) -> str:
        """OpenAI API请求"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.text_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.text_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            payload.update(kwargs)
            
            response = await self._client.post(
                f"{self.config.text_endpoint}/chat/completions",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                logger.error("OpenAI API返回格式异常")
                return ""
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API HTTP错误: {e.response.status_code} - {e.response.text}")
            return ""
        except Exception as e:
            logger.error(f"OpenAI API请求失败: {e}")
            return ""

    async def _anthropic_request(self, messages: List[Dict[str, str]], 
                                max_tokens: int, temperature: float, **kwargs) -> str:
        """Anthropic API请求"""
        try:
            headers = {
                "x-api-key": self.config.text_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # 转换消息格式
            anthropic_messages = []
            system_message = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append(msg)
            
            payload = {
                "model": self.config.text_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": anthropic_messages
            }
            
            if system_message:
                payload["system"] = system_message
                
            payload.update(kwargs)
            
            if self._client:
                response = await self._client.post(
                    f"{self.config.text_endpoint}/messages",
                    headers=headers,
                    json=payload
                )
            else:
                raise RuntimeError("HTTP客户端未初始化")
            
            response.raise_for_status()
            data = response.json()
            
            if "content" in data and len(data["content"]) > 0:
                return data["content"][0]["text"]
            else:
                logger.error("Anthropic API返回格式异常")
                return ""
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API HTTP错误: {e.response.status_code} - {e.response.text}")
            return ""
        except Exception as e:
            logger.error(f"Anthropic API请求失败: {e}")
            return ""

    async def _local_request(self, messages: List[Dict[str, str]], 
                           max_tokens: int, temperature: float, **kwargs) -> str:
        """本地模型API请求（如Ollama）"""
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            # 如果有API密钥，添加到headers
            if self.config.text_api_key and self.config.text_api_key != "":
                headers["Authorization"] = f"Bearer {self.config.text_api_key}"
            
            payload = {
                "model": self.config.text_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            payload.update(kwargs)
            
            response = await self._client.post(
                f"{self.config.text_endpoint}/chat/completions",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                logger.error("本地API返回格式异常")
                return ""
                
        except httpx.HTTPStatusError as e:
            logger.error(f"本地API HTTP错误: {e.response.status_code} - {e.response.text}")
            return ""
        except Exception as e:
            logger.error(f"本地API请求失败: {e}")
            return ""

    async def vision_completion(self, 
                              messages: List[Dict[str, Any]], 
                              image_data: Optional[bytes] = None,
                              max_tokens: int = 1000,
                              **kwargs) -> str:
        """
        视觉理解请求
        
        Args:
            messages: 对话消息列表
            image_data: 图像数据
            max_tokens: 最大令牌数
            **kwargs: 其他参数
            
        Returns:
            模型回复的文本
        """
        if not self._initialized or not self._client:
            logger.error("LLM客户端未初始化")
            return ""
            
        try:
            if image_data:
                # 将图像数据编码为base64
                import base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # 添加图像到消息中
                for message in messages:
                    if message["role"] == "user" and isinstance(message["content"], str):
                        message["content"] = [
                            {"type": "text", "text": message["content"]},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            }
                        ]
                        break
            
            if self.config.vision_provider == "openai":
                return await self._openai_vision_request(messages, max_tokens, **kwargs)
            else:
                logger.error(f"不支持的视觉模型提供商: {self.config.vision_provider}")
                return ""
                
        except Exception as e:
            logger.error(f"视觉理解请求失败: {e}")
            return ""

    async def _openai_vision_request(self, messages: List[Dict[str, Any]], 
                                   max_tokens: int, **kwargs) -> str:
        """OpenAI视觉API请求"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.vision_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.vision_model,
                "messages": messages,
                "max_tokens": max_tokens
            }
            payload.update(kwargs)
            
            if self._client:
                response = await self._client.post(
                    f"{self.config.vision_endpoint}/chat/completions",
                    headers=headers,
                    json=payload
                )
            else:
                raise RuntimeError("HTTP客户端未初始化")
            
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                logger.error("OpenAI视觉API返回格式异常")
                return ""
                
        except Exception as e:
            logger.error(f"OpenAI视觉API请求失败: {e}")
            return ""

    def _update_stats(self, latency: float, response_length: int):
        """更新统计信息"""
        self.stats["total_requests"] += 1
        self.stats["total_tokens"] += response_length
        
        # 计算平均延迟
        total_latency = self.stats["avg_latency"] * (self.stats["total_requests"] - 1) + latency
        self.stats["avg_latency"] = total_latency / self.stats["total_requests"]

    async def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量"""
        # 这是一个简化的估算，实际可以使用tiktoken等库
        # 中文：1个字符约1个token
        # 英文：1个单词约1.3个token
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_words = len([w for w in text.split() if w.isascii()])
        other_chars = len(text) - chinese_chars
        
        estimated_tokens = chinese_chars + int(english_words * 1.3) + int(other_chars * 0.5)
        return max(estimated_tokens, 1)

    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "text_provider": self.config.text_provider,
            "text_model": self.config.text_model,
            "text_endpoint": self.config.text_endpoint,
            "vision_provider": self.config.vision_provider,
            "vision_model": self.config.vision_model,
            "initialized": self._initialized,
            "stats": self.stats.copy()
        }

    async def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "avg_latency": 0.0,
            "errors": 0
        }
        logger.info("LLM统计信息已重置")

    async def test_model(self) -> bool:
        """测试模型可用性"""
        try:
            test_messages = [
                {"role": "user", "content": "请回复'测试成功'"}
            ]
            
            response = await self.chat_completion(test_messages, max_tokens=10)
            
            if response and "测试" in response:
                logger.info("LLM模型测试成功")
                return True
            else:
                logger.warning(f"LLM模型测试响应异常: {response}")
                return False
                
        except Exception as e:
            logger.error(f"LLM模型测试失败: {e}")
            return False

    async def cleanup(self):
        """清理资源"""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
                
            self._initialized = False
            logger.info("LLM客户端资源已清理")
            
        except Exception as e:
            logger.error(f"LLM客户端清理失败: {e}")

    # 配置更新方法
    def update_config(self, **kwargs):
        """动态更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"LLM配置更新: {key} = {value}")

    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if self.config.text_provider == "openai":
            return [
                "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
                "gpt-4-vision-preview", "gpt-4-1106-preview"
            ]
        elif self.config.text_provider == "anthropic":
            return [
                "claude-3-opus-20240229", "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307", "claude-2.1", "claude-2.0"
            ]
        elif self.config.text_provider == "local":
            return ["local-model"]  # 需要根据实际本地模型返回
        else:
            return [] 