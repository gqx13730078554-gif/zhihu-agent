"""
知乎 Agent 系统 - 风控闸门 (Safety Gate)
"""
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

from .models import Account, Content, ContentStatus, RiskState, SafetyCheckResult


# AI高风险套话黑名单
AI_BLACKLIST_PHRASES = [
    "近年来", "随着", "在当今", "不可否认",
    "毫无疑问", "值得注意的是", "综上", "从长期来看",
    "总的来说", "毋庸置疑", "众所周知", "不言而喻",
    "需要指出的是", "应该看到", "事实上", "毫无疑问",
]

# AI模板结构模式
AI_TEMPLATE_PATTERNS = [
    r"首先[，,].*其次[，,].*再次[，,].*最后",
    r"一方面[，,].*另一方面",
    r"背景介绍.*亮点.*影响.*总结",
    r"一是.*二是.*三是.*四是",
]

# 真人写作正面信号
HUMAN_SIGNALS = [
    r"我(用过|测过|试过|遇到过|觉得|认为)",
    r"(截图|价格|参数|实测|对比)",
    r"(不推荐|不适合|别买|慎用)",
    r"(坑|踩雷|翻车|失败)",
]


@dataclass
class GateConfig:
    """闸门配置"""
    # 通用闸门
    require_human_scenario: bool = True
    require_clear_opinion: bool = True
    require_verifiable_detail: bool = True
    require_natural_structure: bool = True
    no_ai_phrases: bool = True
    no_template_pattern: bool = True
    
    # L4专用
    l4_require_direct_judgment: bool = True
    l4_require_tradeoff: bool = True
    l4_require_natural_product: bool = True
    
    # L6专用
    l6_require_conflict_opening: bool = True
    l6_require_real_characters: bool = True
    l6_require_plot_twist: bool = True
    
    # 恢复期专用
    recovery_no_repeat_structure: bool = True
    recovery_human_first_para: bool = True
    recovery_max_one_per_topic_48h: bool = True


class SafetyGate:
    """风控闸门"""
    
    def __init__(self, config: GateConfig = None):
        self.config = config or GateConfig()
    
    def check(self, content: Content, account: Account) -> SafetyCheckResult:
        """执行完整闸门检查"""
        checks = {}
        issues = []
        suggestions = []
        
        # ===== Layer 1: 通用闸门 =====
        
        # 1. 具体人类场景
        checks["human_scenario"] = self._check_human_scenario(content)
        if not checks["human_scenario"]:
            issues.append("缺少具体人类场景")
            suggestions.append("补充：我为什么关心这个问题，谁会遇到，具体到职业/预算/设备")
        
        # 2. 明确主判断
        checks["clear_opinion"] = self._check_clear_opinion(content)
        if not checks["clear_opinion"]:
            issues.append("缺少明确主判断")
            suggestions.append("避免'有利有弊、还需观察'，给出明确倾向")
        
        # 3. 可验证细节
        checks["verifiable_detail"] = self._check_verifiable_detail(content)
        if not checks["verifiable_detail"]:
            issues.append("缺少可验证细节")
            suggestions.append("补充：截图/价格/参数/实测/对比/历史经验至少一种")
        
        # 4. 自然结构
        checks["natural_structure"] = self._check_natural_structure(content)
        if not checks["natural_structure"]:
            issues.append("结构过于工整，像AI模板")
            suggestions.append("打破对称结构，允许不工整，句子长短不一")
        
        # 5. 无AI套话
        checks["no_ai_phrases"] = self._check_no_ai_phrases(content)
        if not checks["no_ai_phrases"]:
            issues.append("包含AI常见套话")
            suggestions.append("删除：近年来/随着/在当今/综上/从长期来看等")
        
        # 6. 无模板模式
        checks["no_template"] = self._check_no_template(content)
        if not checks["no_template"]:
            issues.append("结构像AI模板")
            suggestions.append("避免：首先/其次/再次/最后 或 一是/二是/三是")
        
        # ===== Layer 2: 账号专用闸门 =====
        
        if account.role.value == "ai_programmer_goods":
            # L4 专用检查
            checks["l4_direct_judgment"] = self._check_l4_direct_judgment(content)
            if not checks["l4_direct_judgment"]:
                issues.append("L4: 首段没有直接给判断")
                suggestions.append("第一段直接说：这东西值不值得买/用，适合谁，不适合谁")
            
            checks["l4_tradeoff"] = self._check_l4_tradeoff(content)
            if not checks["l4_tradeoff"]:
                issues.append("L4: 缺少真实取舍")
                suggestions.append("写清：谁适合、谁不适合、坑点、替代方案")
            
            checks["l4_natural_product"] = self._check_l4_natural_product(content)
            if not checks["l4_natural_product"]:
                issues.append("L4: 商品植入不自然")
                suggestions.append("先讲痛点和选择逻辑，再出现工具/商品")
        
        elif account.role.value == "salt_story_suspense":
            # L6 专用检查
            checks["l6_conflict_opening"] = self._check_l6_conflict_opening(content)
            if not checks["l6_conflict_opening"]:
                issues.append("L6: 开头缺少冲突")
                suggestions.append("开头100字内必须有：人物 + 异常 + 冲突细节")
            
            checks["l6_real_characters"] = self._check_l6_real_characters(content)
            if not checks["l6_real_characters"]:
                issues.append("L6: 人物像工具人")
                suggestions.append("人物说话要有口癖、利益和隐瞒")
            
            checks["l6_plot_twist"] = self._check_l6_plot_twist(content)
            if not checks["l6_plot_twist"]:
                issues.append("L6: 缺少反转")
                suggestions.append("每800-1200字必须有一次信息翻转")
        
        # ===== Layer 3: 恢复期闸门 =====
        
        if account.is_recovery_mode():
            checks["recovery_no_repeat"] = self._check_recovery_no_repeat(content, account)
            if not checks["recovery_no_repeat"]:
                issues.append("恢复期: 结构与近期折叠内容相似")
                suggestions.append("不要沿用被折叠内容的同款开头、同款结构")
            
            checks["recovery_human_first"] = self._check_recovery_human_first(content)
            if not checks["recovery_human_first"]:
                issues.append("恢复期: 首段可能由AI生成")
                suggestions.append("首段必须由人工直写")
        
        # ===== 计算总分 =====
        passed_count = sum(1 for v in checks.values() if v)
        total_count = len(checks)
        score = (passed_count / total_count) * 10 if total_count > 0 else 0
        passed = passed_count == total_count
        
        return SafetyCheckResult(
            passed=passed,
            score=score,
            checks=checks,
            issues=issues,
            suggestions=suggestions,
        )
    
    def _check_human_scenario(self, content: Content) -> bool:
        """检查是否有具体人类场景"""
        body = content.body
        
        # 正面信号
        scenario_patterns = [
            r"我(在|用|写|做|遇到)",
            r"(程序员|开发者|设计师|学生)(在|用|需要)",
            r"(昨天|上周|最近|上个月)",
            r"(预算|价格|成本|花费)",
            r"(电脑|设备|环境|场景)",
        ]
        
        for pattern in scenario_patterns:
            if re.search(pattern, body):
                return True
        
        return False
    
    def _check_clear_opinion(self, content: Content) -> bool:
        """检查是否有明确观点"""
        body = content.body
        
        # 中立/模糊信号（扣分）
        neutral_patterns = [
            r"(有利有弊|还需观察|因人而异|各有优劣)",
            r"(不能简单地说|需要辩证看待)",
        ]
        
        # 明确观点信号（加分）
        opinion_patterns = [
            r"(我(认为|觉得|建议|推荐|不推荐))",
            r"(值得|不值得|适合|不适合)",
            r"(买|不买|用|不用)",
        ]
        
        has_neutral = any(re.search(p, body) for p in neutral_patterns)
        has_opinion = any(re.search(p, body) for p in opinion_patterns)
        
        return has_opinion and not has_neutral
    
    def _check_verifiable_detail(self, content: Content) -> bool:
        """检查是否有可验证细节"""
        body = content.body
        
        evidence_patterns = [
            r"\d+(元|块|刀|\$)",           # 价格
            r"\d+(GB|TB|MHz|nm)",          # 参数
            r"(截图|图片|如图)",            # 截图
            r"(实测|测试|体验)",            # 实测
            r"(对比|vs|VS)",                # 对比
        ]
        
        return any(re.search(p, body) for p in evidence_patterns)
    
    def _check_natural_structure(self, content: Content) -> bool:
        """检查结构是否自然"""
        body = content.body
        
        # 检查段落长度是否过于均匀
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        if len(paragraphs) >= 3:
            lengths = [len(p) for p in paragraphs]
            avg = sum(lengths) / len(lengths)
            variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
            
            # 方差太小说明段落长度太均匀
            if variance < 100:
                return False
        
        return True
    
    def _check_no_ai_phrases(self, content: Content) -> bool:
        """检查是否包含AI套话"""
        body = content.body.lower()
        
        for phrase in AI_BLACKLIST_PHRASES:
            if phrase in body:
                return False
        
        return True
    
    def _check_no_template(self, content: Content) -> bool:
        """检查是否包含模板结构"""
        body = content.body
        
        for pattern in AI_TEMPLATE_PATTERNS:
            if re.search(pattern, body, re.DOTALL):
                return False
        
        return True
    
    def _check_l4_direct_judgment(self, content: Content) -> bool:
        """L4: 检查首段是否直接给判断"""
        first_para = content.body.split("\n\n")[0] if "\n\n" in content.body else content.body[:200]
        
        judgment_patterns = [
            r"(值得|不值得|推荐|不推荐)",
            r"(适合|不适合)",
            r"(买|不买|用|不用)",
            r"(好|差|强|弱)",
        ]
        
        return any(re.search(p, first_para) for p in judgment_patterns)
    
    def _check_l4_tradeoff(self, content: Content) -> bool:
        """L4: 检查是否有真实取舍"""
        body = content.body
        
        tradeoff_patterns = [
            r"(适合.*不适合)",
            r"(推荐.*不推荐)",
            r"(优点.*缺点)",
            r"(坑|踩雷|问题|但是)",
        ]
        
        return any(re.search(p, body) for p in tradeoff_patterns)
    
    def _check_l4_natural_product(self, content: Content) -> bool:
        """L4: 检查商品植入是否自然"""
        if not content.products:
            return True  # 没有商品植入，通过
        
        body = content.body
        
        # 检查商品出现前是否有场景/痛点描述
        product_names = [p.name for p in content.products]
        
        for name in product_names:
            idx = body.find(name)
            if idx > 0:
                # 检查商品前200字是否有场景描述
                before_text = body[max(0, idx-200):idx]
                scenario_patterns = [
                    r"(痛点|问题|需求|场景)",
                    r"(我|你|用户)(需要|遇到|想要)",
                ]
                if any(re.search(p, before_text) for p in scenario_patterns):
                    return True
        
        return False
    
    def _check_l6_conflict_opening(self, content: Content) -> bool:
        """L6: 检查开头是否有冲突"""
        first_200 = content.body[:200]
        
        conflict_patterns = [
            r"(突然|忽然|没想到)",
            r"(奇怪|诡异|异常|不对劲)",
            r"(发现|看到|听到)",
            r"(死|血|影子|声音)",
        ]
        
        return any(re.search(p, first_200) for p in conflict_patterns)
    
    def _check_l6_real_characters(self, content: Content) -> bool:
        """L6: 检查人物是否立体"""
        body = content.body
        
        # 检查是否有对话
        dialogue_patterns = [
            r"[「「""].*[」」""]",
            r"[：:]",
        ]
        
        has_dialogue = any(re.search(p, body) for p in dialogue_patterns)
        
        # 检查人物是否有具体特征
        character_patterns = [
            r"(老[王李张]|小[明红]|师傅|老板)",
            r"(他|她).*(说|笑|看|想)",
        ]
        
        has_character = any(re.search(p, body) for p in character_patterns)
        
        return has_dialogue and has_character
    
    def _check_l6_plot_twist(self, content: Content) -> bool:
        """L6: 检查是否有反转"""
        body = content.body
        word_count = len(body)
        
        # 每800-1200字应该有一次翻转
        expected_twists = word_count // 1000
        
        twist_patterns = [
            r"(但是|然而|没想到|竟然)",
            r"(原来|其实|事实上)",
            r"(反转|真相)",
        ]
        
        twist_count = sum(1 for p in twist_patterns if re.search(p, body))
        
        return twist_count >= expected_twists
    
    def _check_recovery_no_repeat(self, content: Content, account: Account) -> bool:
        """恢复期: 检查是否与近期折叠内容结构相似"""
        # TODO: 实现与历史折叠内容的结构对比
        # 这里简化处理
        return True
    
    def _check_recovery_human_first(self, content: Content) -> bool:
        """恢复期: 检查首段是否人工直写"""
        # TODO: 实现首段来源追踪
        # 这里简化处理
        return True


def run_safety_gate(content: Content, account: Account) -> SafetyCheckResult:
    """运行风控闸门"""
    gate = SafetyGate()
    return gate.check(content, account)
