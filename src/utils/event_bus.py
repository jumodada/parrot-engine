"""
事件总线系统
用于模块间的解耦通信
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from loguru import logger
import weakref


@dataclass
class Event:
    """事件数据类"""
    type: str
    data: Any = None
    source: Optional[str] = None
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()


class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Any]] = {}
        self._async_subscribers: Dict[str, List[Any]] = {}
        self._lock = asyncio.Lock()
    
    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        """订阅同步事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
            
        # 使用弱引用避免内存泄漏
        weak_callback = weakref.WeakMethod(callback) if hasattr(callback, '__self__') else callback
        self._subscribers[event_type].append(weak_callback)
        
        logger.debug(f"订阅事件: {event_type}")
    
    def subscribe_async(self, event_type: str, callback: Callable[[Event], None]):
        """订阅异步事件"""
        if event_type not in self._async_subscribers:
            self._async_subscribers[event_type] = []
            
        weak_callback = weakref.WeakMethod(callback) if hasattr(callback, '__self__') else callback
        self._async_subscribers[event_type].append(weak_callback)
        
        logger.debug(f"订阅异步事件: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]):
        """取消订阅同步事件"""
        if event_type in self._subscribers:
            # 清理对应的回调
            callbacks = self._subscribers[event_type]
            self._subscribers[event_type] = [
                cb for cb in callbacks 
                if (hasattr(cb, '__self__') and cb() != callback) or cb != callback
            ]
        
        logger.debug(f"取消订阅事件: {event_type}")
    
    def unsubscribe_async(self, event_type: str, callback: Callable[[Event], None]):
        """取消订阅异步事件"""
        if event_type in self._async_subscribers:
            callbacks = self._async_subscribers[event_type]
            self._async_subscribers[event_type] = [
                cb for cb in callbacks 
                if (hasattr(cb, '__self__') and cb() != callback) or cb != callback
            ]
        
        logger.debug(f"取消订阅异步事件: {event_type}")
    
    def emit(self, event_type: str, data: Any = None, source: Optional[str] = None):
        """发送同步事件"""
        event = Event(type=event_type, data=data, source=source)
        
        # 清理失效的弱引用
        if event_type in self._subscribers:
            valid_callbacks = []
            for callback_ref in self._subscribers[event_type]:
                if isinstance(callback_ref, weakref.WeakMethod):
                    callback = callback_ref()
                    if callback is not None:
                        valid_callbacks.append(callback_ref)
                        try:
                            callback(event)
                        except Exception as e:
                            logger.error(f"事件回调执行失败: {e}")
                else:
                    valid_callbacks.append(callback_ref)
                    try:
                        callback_ref(event)
                    except Exception as e:
                        logger.error(f"事件回调执行失败: {e}")
            
            self._subscribers[event_type] = valid_callbacks
        
        logger.debug(f"发送事件: {event_type}")
    
    async def emit_async(self, event_type: str, data: Any = None, source: Optional[str] = None):
        """发送异步事件"""
        event = Event(type=event_type, data=data, source=source)
        
        async with self._lock:
            if event_type in self._async_subscribers:
                valid_callbacks = []
                tasks = []
                
                for callback_ref in self._async_subscribers[event_type]:
                    if isinstance(callback_ref, weakref.WeakMethod):
                        callback = callback_ref()
                        if callback is not None:
                            valid_callbacks.append(callback_ref)
                            if asyncio.iscoroutinefunction(callback):
                                tasks.append(callback(event))
                            else:
                                try:
                                    callback(event)
                                except Exception as e:
                                    logger.error(f"异步事件回调执行失败: {e}")
                    else:
                        valid_callbacks.append(callback_ref)
                        if asyncio.iscoroutinefunction(callback_ref):
                            tasks.append(callback_ref(event))
                        else:
                            try:
                                callback_ref(event)
                            except Exception as e:
                                logger.error(f"异步事件回调执行失败: {e}")
                
                self._async_subscribers[event_type] = valid_callbacks
                
                # 并行执行所有异步回调
                if tasks:
                    try:
                        await asyncio.gather(*tasks, return_exceptions=True)
                    except Exception as e:
                        logger.error(f"异步事件处理失败: {e}")
        
        logger.debug(f"发送异步事件: {event_type}")
    
    def clear_subscribers(self, event_type: Optional[str] = None):
        """清理订阅者"""
        if event_type:
            if event_type in self._subscribers:
                del self._subscribers[event_type]
            if event_type in self._async_subscribers:
                del self._async_subscribers[event_type]
        else:
            self._subscribers.clear()
            self._async_subscribers.clear()
        
        logger.debug(f"清理订阅者: {event_type or '所有'}")
    
    def get_subscriber_count(self, event_type: str) -> int:
        """获取订阅者数量"""
        sync_count = len(self._subscribers.get(event_type, []))
        async_count = len(self._async_subscribers.get(event_type, []))
        return sync_count + async_count
    
    def get_all_event_types(self) -> List[str]:
        """获取所有事件类型"""
        types = set()
        types.update(self._subscribers.keys())
        types.update(self._async_subscribers.keys())
        return list(types)


# 全局事件总线实例
global_event_bus = EventBus()


# 便捷函数
def subscribe(event_type: str, callback: Callable[[Event], None]):
    """订阅全局事件"""
    global_event_bus.subscribe(event_type, callback)


def subscribe_async(event_type: str, callback: Callable[[Event], None]):
    """订阅全局异步事件"""
    global_event_bus.subscribe_async(event_type, callback)


def emit(event_type: str, data: Any = None, source: Optional[str] = None):
    """发送全局事件"""
    global_event_bus.emit(event_type, data, source)


async def emit_async(event_type: str, data: Any = None, source: Optional[str] = None):
    """发送全局异步事件"""
    await global_event_bus.emit_async(event_type, data, source) 