"""
翻译模块 - 支持多种免费/低价方案
优先级:
1. MiniMax API (低价 chat API 做翻译, ~¥0.1/百万字)
2. Google Translate (免费但可能被屏蔽)
3. 基础词典替换 (完全免费, 无网络依赖)
"""
import re
import logging
from typing import Optional
from pathlib import Path
from loguru import logger

from .config import TEMP_DIR, MINIMAX_API_KEY

# 语言代码映射
LANG_MAP = {
    "zh": "zh-CN", "en": "en", "ja": "ja", "ko": "ko",
    "fr": "fr", "de": "de", "es": "es", "it": "it",
    "ru": "ru", "ar": "ar", "pt": "pt", "nl": "nl",
}


class MiniMaxChatTranslator:
    """
    MiniMax Chat API 翻译
    使用 chat completion 做翻译，成本极低
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or MINIMAX_API_KEY
        self.api_base = "https://api.minimax.chat/v1"
        self.model = "abab6.5s-chat"
        
        if not self.api_key:
            raise ValueError("MiniMax API key required")
    
    def translate(self, text: str, source_lang: str = "en", target_lang: str = "zh") -> str:
        """翻译文本"""
        if not text.strip():
            return text
        
        import requests
        
        # 构建 prompt
        src = LANG_MAP.get(source_lang, source_lang)
        tgt = LANG_MAP.get(target_lang, target_lang)
        
        prompt = f"""Translate the following {src} text to {tgt}. 
Only output the translated text, nothing else.

Text: {text}

{tgt} translation:"""
        
        try:
            resp = requests.post(
                f"{self.api_base}/text/chatcompletion_v2",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.1,
                },
                timeout=30,
            )
            
            data = resp.json()
            
            if "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"API error: {data}")
                return f"[翻译失败] {text}"
                
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return f"[翻译失败] {text}"
    
    def translate_batch(self, texts: list, source_lang: str = "en", target_lang: str = "zh") -> list:
        """批量翻译"""
        return [self.translate(t, source_lang, target_lang) for t in texts]
    
    def translate_srt(self, srt_content: str, source_lang: str = "en", target_lang: str = "zh") -> str:
        """翻译 SRT"""
        from .translator import parse_srt, create_srt
        
        blocks = parse_srt(srt_content)
        texts = [b["text"] for b in blocks]
        
        logger.info(f"Translating {len(texts)} subtitle blocks...")
        translated = self.translate_batch(texts, source_lang, target_lang)
        
        for block, trans_text in zip(blocks, translated):
            block["text"] = trans_text
        
        return create_srt(blocks)


class GoogleTranslator:
    """
    Google Translate 免费翻译
    使用 deep-translator 封装
    """
    
    def __init__(self):
        self._gt = None
        logger.info("GoogleTranslator initialized")
    
    @property
    def gt(self):
        if self._gt is None:
            from deep_translator import GoogleTranslator as GT
            self._gt = GT
        return self._gt
    
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "zh") -> str:
        if not text.strip():
            return text
        
        src = LANG_MAP.get(source_lang, source_lang)
        tgt = LANG_MAP.get(target_lang, target_lang)
        
        try:
            return self.gt(source=src, target=tgt).translate(text)
        except Exception as e:
            logger.error(f"Google translate error: {e}")
            return f"[翻译失败] {text}"
    
    def translate_batch(self, texts: list, source_lang: str = "auto", target_lang: str = "zh") -> list:
        return [self.translate(t, source_lang, target_lang) for t in texts]
    
    def translate_srt(self, srt_content: str, source_lang: str = "en", target_lang: str = "zh") -> str:
        from .translator import parse_srt, create_srt
        
        blocks = parse_srt(srt_content)
        translated = self.translate_batch([b["text"] for b in blocks], source_lang, target_lang)
        
        for block, trans_text in zip(blocks, translated):
            block["text"] = trans_text
        
        return create_srt(blocks)


class BasicDictionaryTranslator:
    """
    基础词典翻译 - 完全免费无需网络
    使用简单的中英词典进行词组替换
    """
    
    # 常用中英词典
    DICT = {
        "hello": "你好", "hi": "你好", "goodbye": "再见", "bye": "再见",
        "thank": "谢谢", "thanks": "谢谢", "you": "你", "i": "我",
        "the": "", "is": "是", "are": "是", "was": "是", "were": "是",
        "this": "这", "that": "那", "it": "它", "he": "他", "she": "她",
        "we": "我们", "they": "他们", "what": "什么", "where": "哪里",
        "when": "什么时候", "who": "谁", "why": "为什么", "how": "怎么",
        "yes": "是", "no": "不", "please": "请", "sorry": "对不起",
        "good": "好", "bad": "坏", "big": "大", "small": "小",
        "new": "新", "old": "旧", "hot": "热", "cold": "冷",
        "fast": "快", "slow": "慢", "up": "上", "down": "下",
        "left": "左", "right": "右", "come": "来", "go": "去",
        "eat": "吃", "drink": "喝", "sleep": "睡觉", "walk": "走",
        "run": "跑", "see": "看", "hear": "听", "speak": "说",
        "think": "想", "know": "知道", "want": "想要", "need": "需要",
        "like": "喜欢", "love": "爱", "hate": "讨厌", "have": "有",
        "get": "得到", "make": "做", "take": "拿", "give": "给",
        "time": "时间", "day": "天", "night": "晚上", "year": "年",
        "month": "月", "week": "周", "hour": "小时", "minute": "分钟",
        "welcome": "欢迎", "system": "系统", "test": "测试", "video": "视频",
        "audio": "音频", "translation": "翻译", "voice": "声音", "speech": "语音",
        "language": "语言", "word": "词", "text": "文本", "file": "文件",
        "image": "图片", "photo": "照片", "music": "音乐", "song": "歌曲",
        "movie": "电影", "film": "电影", "story": "故事", "news": "新闻",
        "weather": "天气", "today": "今天", "tomorrow": "明天", "yesterday": "昨天",
        "morning": "早上", "afternoon": "下午", "evening": "晚上",
        "water": "水", "food": "食物", "rice": "米饭", "bread": "面包",
        "meat": "肉", "fish": "鱼", "egg": "蛋", "vegetable": "蔬菜",
        "fruit": "水果", "apple": "苹果", "banana": "香蕉", "orange": "橙子",
        "car": "车", "bus": "公交车", "train": "火车", "plane": "飞机",
        "ship": "船", "bike": "自行车", "road": "路", "street": "街",
        "house": "房子", "home": "家", "room": "房间", "door": "门",
        "window": "窗户", "table": "桌子", "chair": "椅子", "bed": "床",
        "book": "书", "paper": "纸", "pen": "笔", "computer": "电脑",
        "phone": "手机", "camera": "相机", "clock": "时钟", "watch": "手表",
        "color": "颜色", "red": "红", "blue": "蓝", "green": "绿",
        "yellow": "黄", "white": "白", "black": "黑", "dog": "狗",
        "cat": "猫", "bird": "鸟", "fish": "鱼", "tree": "树",
        "flower": "花", "grass": "草", "river": "河", "mountain": "山",
        "sea": "海", "sky": "天空", "sun": "太阳", "moon": "月亮",
        "star": "星星", "cloud": "云", "rain": "雨", "snow": "雪",
        "wind": "风", "fire": "火", "earth": "地球", "world": "世界",
        "country": "国家", "china": "中国", "america": "美国", "english": "英语",
        "chinese": "中文", "japanese": "日语", "french": "法语", "german": "德语",
    }
    
    def __init__(self):
        logger.info("BasicDictionaryTranslator initialized (offline)")
    
    def translate(self, text: str, source_lang: str = "en", target_lang: str = "zh") -> str:
        """简单词典替换翻译"""
        if not text.strip() or target_lang != "zh":
            return text
        
        words = re.findall(r'[a-zA-Z]+', text.lower())
        result = text
        
        for word in set(words):
            if word in self.DICT:
                chinese = self.DICT[word]
                # 替换时保持大小写
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                result = pattern.sub(chinese, result)
        
        return result
    
    def translate_batch(self, texts: list, source_lang: str = "en", target_lang: str = "zh") -> list:
        return [self.translate(t, source_lang, target_lang) for t in texts]
    
    def translate_srt(self, srt_content: str, source_lang: str = "en", target_lang: str = "zh") -> str:
        from .translator import parse_srt, create_srt
        
        blocks = parse_srt(srt_content)
        translated = self.translate_batch([b["text"] for b in blocks], source_lang, target_lang)
        
        for block, trans_text in zip(blocks, translated):
            block["text"] = trans_text
        
        return create_srt(blocks)


def get_translator():
    """
    获取可用的翻译器
    优先级: MiniMax API > Google Translate > 基础词典
    """
    # 1. 尝试 MiniMax API
    if MINIMAX_API_KEY:
        try:
            t = MiniMaxChatTranslator()
            t.translate("test", "en", "zh")
            logger.info("Using MiniMax API for translation")
            return t
        except Exception as e:
            logger.warning(f"MiniMax API failed: {e}")
    
    # 2. 尝试 Google Translate
    try:
        import requests
        requests.get("https://translate.google.com", timeout=5)
        t = GoogleTranslator()
        t.translate("test", "en", "zh")
        logger.info("Using Google Translate")
        return t
    except Exception as e:
        logger.warning(f"Google Translate unavailable: {e}")
    
    # 3. 使用基础词典
    logger.info("Using Basic Dictionary (offline)")
    return BasicDictionaryTranslator()


if __name__ == "__main__":
    # 测试
    t = get_translator()
    print(f"Using: {type(t).__name__}")
    
    tests = ["Hello, this is a test.", "Welcome to the system.", "How are you?"]
    for text in tests:
        print(f"  {text} -> {t.translate(text, 'en', 'zh')}")