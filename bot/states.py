"""
State های مختلف برای ConversationHandler
"""
from enum import IntEnum


class ConversationStates(IntEnum):
    """state های مختلف مکالمه با کاربر"""
    
    # مراحل Setup اولیه
    CHOOSING_GENRE = 1
    SETTING_TIME = 2
    CHOOSING_DESTINATION = 3
    SETTING_CHANNEL = 4
    
    # مراحل تنظیمات
    CHANGING_GENRE = 10
    CHANGING_TIME = 11
    CHANGING_DESTINATION = 12
    CHANGING_CHANNEL = 13
    
    # وضعیت‌های دیگر
    WAITING_INPUT = 20
    CONFIRMING = 21


# برای راحتی استفاده
CHOOSING_GENRE = ConversationStates.CHOOSING_GENRE
SETTING_TIME = ConversationStates.SETTING_TIME
CHOOSING_DESTINATION = ConversationStates.CHOOSING_DESTINATION
SETTING_CHANNEL = ConversationStates.SETTING_CHANNEL

CHANGING_GENRE = ConversationStates.CHANGING_GENRE
CHANGING_TIME = ConversationStates.CHANGING_TIME
CHANGING_DESTINATION = ConversationStates.CHANGING_DESTINATION
CHANGING_CHANNEL = ConversationStates.CHANGING_CHANNEL

WAITING_INPUT = ConversationStates.WAITING_INPUT
CONFIRMING = ConversationStates.CONFIRMING