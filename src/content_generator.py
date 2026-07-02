"""
知乎 Agent 系统 - 内容生成引擎（新版）
核心：分步生成 + 真人信号注入
"""
import random
from typing import List, Dict
from dataclasses import dataclass

from .models import Account, Topic, Content, ContentStatus


@dataclass
class HumanSignal:
    """真人信号"""
    category: str
    text: str
    injected: bool = False


# 真人信号库
HUMAN_SIGNAL_LIBRARY = {
    "personal_experience": [
        "我上周遇到的一个问题...",
        "我用这个工具三个月了...",
        "我当时预算只有XXX...",
        "我同事推荐给我的...",
        "我之前试过另一个工具...",
        "我朋友是程序员，他推荐我用的...",
        "我上个月刚买了一个...",
        "我当时纠结了很久，最后选了这个...",
    ],
    "specific_details": [
        "价格是¥299/月",
        "8GB内存版本",
        "用了3天",
        "在MacBook Pro上测试",
        "响应速度大概200ms",
        "文件大小只有50MB",
        "支持Windows/Mac/Linux",
        "有免费版和Pro版",
    ],
    "emotional_expression": [
        "说实话，有点失望",
        "这个功能真的惊艳到我了",
        "踩坑踩得我想骂人",
        "后悔没早点发现",
        "用了一次就爱上了",
        "感觉一般般吧",
        "性价比很高，满意",
        "有点贵，但值这个价",
    ],
    "imperfection": [
        "可能我说得不太专业",
        "这只是我的个人体验",
        "不确定是不是个例",
        "反正我是这么觉得的",
        "不知道别人用起来怎么样",
        "可能我的场景比较特殊",
        "仅供参考吧",
        "不一定适合所有人",
    ],
    "casual_language": [
        "说白了",
        "其实吧",
        "怎么说呢",
        "emmm",
        "哈哈哈",
        "真的绝了",
        "我直接好家伙",
        "有一说一",
    ],
}


class HumanSignalInjector:
    """真人信号注入器"""
    
    def __init__(self):
        self.library = HUMAN_SIGNAL_LIBRARY
    
    def generate_signal_pack(self, topic: Topic, account: Account) -> Dict[str, List[str]]:
        """生成真人信号包"""
        pack = {}
        
        # 每个类别随机选择1-2个信号
        for category, signals in self.library.items():
            count = random.randint(1, 2)
            selected = random.sample(signals, min(count, len(signals)))
            pack[category] = selected
        
        return pack
    
    def inject_signals(self, content: str, signal_pack: Dict[str, List[str]]) -> str:
        """将信号注入内容"""
        # 这里简化处理，实际应该更智能地插入
        # 在合适的位置插入信号
        
        # 在开头插入个人经历
        if "personal_experience" in signal_pack:
            experience = signal_pack["personal_experience"][0]
            content = content.replace("## 我的体验", f"## 我的体验\n\n{experience}")
        
        # 在中间插入具体细节
        if "specific_details" in signal_pack:
            details = signal_pack["specific_details"]
            for detail in details[:2]:
                content = content.replace("优点：", f"优点：{detail}，")
        
        # 插入情绪表达
        if "emotional_expression" in signal_pack:
            emotion = signal_pack["emotional_expression"][0]
            content = content.replace("总的来说", f"{emotion}。\n\n总的来说")
        
        # 插入不完美表达
        if "imperfection" in signal_pack:
            imperfection = signal_pack["imperfection"][0]
            content = content.replace("适合：", f"{imperfection}\n\n适合：")
        
        return content


class ContentGenerator:
    """内容生成器（新版）"""
    
    def __init__(self):
        self.signal_injector = HumanSignalInjector()
    
    def generate_content(self, topic: Topic, account: Account) -> Content:
        """生成内容（分步生成）"""
        
        # Step 1: 生成真人信号包
        signal_pack = self.signal_injector.generate_signal_pack(topic, account)
        
        # Step 2: 基于信号包生成文章
        content_body = self._generate_with_signals(topic, account, signal_pack)
        
        # Step 3: 创建Content对象
        content = Content(
            id=f"c_{random.randint(1000, 9999)}",
            account_key=account.key,
            topic=topic,
            content_type="answer",
            title=f"如何评价{topic.title}？",
            body=content_body,
            word_count=len(content_body),
            status=ContentStatus.PENDING_REVIEW,
        )
        
        return content
    
    def _generate_with_signals(self, topic: Topic, account: Account, signal_pack: Dict) -> str:
        """基于信号包生成文章"""
        
        # 根据账号角色生成不同风格的内容
        if account.role.value == "ai_programmer_goods":
            return self._generate_l4_content(topic, signal_pack)
        elif account.role.value == "salt_story_suspense":
            return self._generate_l6_content(topic, signal_pack)
        else:
            return self._generate_generic_content(topic, signal_pack)
    
    def _generate_l4_content(self, topic: Topic, signal_pack: Dict) -> str:
        """生成L4 AI/程序员好物内容"""
        
        # 选择信号
        experience = signal_pack.get("personal_experience", [""])[0]
        details = signal_pack.get("specific_details", ["", ""])
        emotion = signal_pack.get("emotional_expression", [""])[0]
        imperfection = signal_pack.get("imperfection", [""])[0]
        casual = signal_pack.get("casual_language", [""])[0]
        
        content = f"""
{casual}，我直接说结论：**值得买，但不适合所有人**。

{experience}

## 我的使用场景

我是一个后端程序员，日常需要处理大量代码。之前试过不少工具，踩了不少坑。

{imperfection}

## 实测体验

{details[0]}，我用了大概一周时间。

{emotion}

优点：
- 响应速度快
- 代码质量高
- 学习成本低

缺点：
- 价格有点贵
- 某些功能还不够完善

## 谁适合买

适合：有预算的专业开发者，追求效率的人
不适合：学生党，预算有限的人

## 购买建议

现在官网有活动，年付打7折。
链接我放评论区，需要的自取。
"""
        return content.strip()
    
    def _generate_l6_content(self, topic: Topic, signal_pack: Dict) -> str:
        """生成L6故事内容"""
        
        experience = signal_pack.get("personal_experience", [""])[0]
        emotion = signal_pack.get("emotional_expression", [""])[0]
        
        content = f"""
那天晚上发生的事，我到现在都想不明白。

我叫李明，在老家镇上开了一家小卖部。生意不大，但勉强够糊口。

{experience}

那天是农历七月十五，中元节。

晚上十点多，我正在盘点库存，突然听到门外有敲门声。

"咚咚咚"

这么晚了，会是谁呢？

我打开门，外面站着一个穿白衣服的女人。她低着头，长发遮住了脸。

"买东西吗？"我问。

她没说话，只是递过来一张百元大钞。

我接过钱，正准备找零，突然发现不对劲——

{emotion}

那张钱，是湿的。
"""
        return content.strip()
    
    def _generate_generic_content(self, topic: Topic, signal_pack: Dict) -> str:
        """生成通用内容"""
        return self._generate_l4_content(topic, signal_pack)


class QualityChecker:
    """质量检查器"""
    
    def check(self, content: Content) -> Dict[str, bool]:
        """检查内容质量"""
        checks = {
            "has_personal_experience": self._has_personal_experience(content.body),
            "has_specific_details": self._has_specific_details(content.body),
            "has_emotional_expression": self._has_emotional_expression(content.body),
            "has_imperfection": self._has_imperfection(content.body),
            "no_ai_phrases": self._no_ai_phrases(content.body),
            "no_template_structure": self._no_template_structure(content.body),
            "natural_rhythm": self._natural_rhythm(content.body),
            "clear_opinion": self._clear_opinion(content.body),
        }
        
        return checks
    
    def _has_personal_experience(self, body: str) -> bool:
        """是否有个人经历"""
        patterns = ["我", "我的", "我上周", "我用过", "我试过"]
        return any(p in body for p in patterns)
    
    def _has_specific_details(self, body: str) -> bool:
        """是否有具体细节"""
        patterns = ["¥", "元", "GB", "MB", "天", "周", "月"]
        return any(p in body for p in patterns)
    
    def _has_emotional_expression(self, body: str) -> bool:
        """是否有情绪表达"""
        patterns = ["失望", "惊艳", "骂人", "后悔", "爱", "满意"]
        return any(p in body for p in patterns)
    
    def _has_imperfection(self, body: str) -> bool:
        """是否有不完美表达"""
        patterns = ["可能", "个人", "不确定", "反正", "不一定"]
        return any(p in body for p in patterns)
    
    def _no_ai_phrases(self, body: str) -> bool:
        """是否避免了AI套话"""
        ai_phrases = ["近年来", "随着", "在当今", "综上", "从长期来看"]
        return not any(p in body for p in ai_phrases)
    
    def _no_template_structure(self, body: str) -> bool:
        """是否避免了模板结构"""
        template_patterns = ["首先.*其次.*再次.*最后", "一是.*二是.*三是"]
        import re
        return not any(re.search(p, body) for p in template_patterns)
    
    def _natural_rhythm(self, body: str) -> bool:
        """句子长短是否自然"""
        sentences = body.split("。")
        lengths = [len(s) for s in sentences if s.strip()]
        if len(lengths) < 3:
            return True
        # 检查是否有长有短
        return max(lengths) - min(lengths) > 20
    
    def _clear_opinion(self, body: str) -> bool:
        """是否有明确观点"""
        patterns = ["值得", "不值得", "推荐", "不推荐", "适合", "不适合"]
        return any(p in body for p in patterns)
