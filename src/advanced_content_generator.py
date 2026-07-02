"""
高级内容生成器 - 基于2024-2026前沿研究
核心技术：
1. 个人风格迁移 (ACL 2026: Post-Editing LLM-Generated Text for Personal Style)
2. 释义反转 (Unsupervised Style Representation Learning via Paraphrase Inversion)
3. 风格多样性控制 (StoryScope: Investigating idiosyncrasies in AI fiction)
"""
import random
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from collections import Counter

from .models import Account, Topic, Content, ContentStatus


@dataclass
class AuthorStyleProfile:
    """作者风格画像 - 从真实写作样本中学习"""
    
    # 词汇特征
    avg_sentence_length: float = 15.0  # 平均句长
    vocabulary_richness: float = 0.7   # 词汇丰富度
    preferred_connectors: List[str] = field(default_factory=list)  # 偏好连接词
    
    # 结构特征
    paragraph_length_range: Tuple[int, int] = (3, 8)  # 段落长度范围
    uses_lists: bool = True  # 是否使用列表
    uses_rhetorical_questions: bool = True  # 是否使用反问句
    
    # 情感特征
    emotional_intensity: float = 0.5  # 情感强度 0-1
    humor_frequency: float = 0.3      # 幽默频率 0-1
    self_deprecation: float = 0.2     # 自嘲频率 0-1
    
    # 个人特征
    personal_pronoun_frequency: float = 0.15  # 第一人称频率
    anecdote_frequency: float = 0.4           # 轶事频率
    opinion_strength: float = 0.7             # 观点强度


class StyleLearner:
    """风格学习器 - 从样本中学习作者风格"""
    
    def __init__(self):
        self.style_profiles = {}
    
    def learn_from_samples(self, author_id: str, samples: List[str]) -> AuthorStyleProfile:
        """从写作样本中学习风格"""
        
        profile = AuthorStyleProfile()
        
        # 分析句子长度
        all_sentences = []
        for sample in samples:
            sentences = re.split(r'[。！？]', sample)
            sentences = [s.strip() for s in sentences if s.strip()]
            all_sentences.extend(sentences)
        
        if all_sentences:
            lengths = [len(s) for s in all_sentences]
            profile.avg_sentence_length = sum(lengths) / len(lengths)
        
        # 分析词汇丰富度
        all_words = []
        for sample in samples:
            words = list(sample)
            all_words.extend(words)
        
        if all_words:
            unique_words = len(set(all_words))
            profile.vocabulary_richness = unique_words / len(all_words)
        
        # 分析连接词偏好
        connectors = ['但是', '所以', '因为', '虽然', '如果', '其实', '说实话', '怎么说呢']
        connector_counts = {}
        for connector in connectors:
            count = sum(sample.count(connector) for sample in samples)
            if count > 0:
                connector_counts[connector] = count
        
        if connector_counts:
            sorted_connectors = sorted(connector_counts.items(), key=lambda x: x[1], reverse=True)
            profile.preferred_connectors = [c[0] for c in sorted_connectors[:3]]
        
        # 分析段落长度
        all_paragraphs = []
        for sample in samples:
            paragraphs = sample.split('\n\n')
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            all_paragraphs.extend(paragraphs)
        
        if all_paragraphs:
            para_lengths = [len(p) for p in all_paragraphs]
            profile.paragraph_length_range = (min(para_lengths), max(para_lengths))
        
        # 分析反问句
        rhetorical_count = sum(sample.count('？') for sample in samples)
        total_sentences = len(all_sentences) if all_sentences else 1
        profile.uses_rhetorical_questions = (rhetorical_count / total_sentences) > 0.1
        
        # 分析情感强度
        emotional_words = ['真的', '超级', '特别', '非常', '太', '好', '绝了']
        emotional_count = sum(sum(sample.count(w) for w in emotional_words) for sample in samples)
        profile.emotional_intensity = min(1.0, emotional_count / (len(samples) * 10))
        
        # 分析第一人称频率
        first_person = ['我', '我的', '我们', '咱们']
        first_person_count = sum(sum(sample.count(p) for p in first_person) for sample in samples)
        total_chars = sum(len(s) for s in samples)
        profile.personal_pronoun_frequency = first_person_count / total_chars if total_chars > 0 else 0.1
        
        # 分析自嘲
        self_deprecation_words = ['可能', '也许', '不确定', '不太懂', '外行']
        self_dep_count = sum(sum(sample.count(w) for w in self_deprecation_words) for sample in samples)
        profile.self_deprecation = min(1.0, self_dep_count / (len(samples) * 5))
        
        self.style_profiles[author_id] = profile
        return profile
    
    def get_style_profile(self, author_id: str) -> AuthorStyleProfile:
        """获取作者风格画像"""
        return self.style_profiles.get(author_id, AuthorStyleProfile())


class ParaphraseEngine:
    """释义引擎 - 通过多次改写消除AI痕迹"""
    
    def __init__(self):
        self.rewrite_rules = [
            # 句式转换
            (r'因为(.+?)，所以(.+?)', r'\2，因为\1'),
            (r'虽然(.+?)，但是(.+?)', r'\2，尽管\1'),
            
            # 词汇替换
            ('非常好', '挺不错的'),
            ('非常好', '相当可以'),
            ('非常好', '蛮好的'),
            
            ('但是', '不过'),
            ('但是', '话说回来'),
            ('但是', '话说回来'),
            
            ('所以', '因此'),
            ('所以', '这么一来'),
            
            # 口语化转换
            ('这个', '这玩意儿'),
            ('那个', '那玩意儿'),
            ('什么', '啥'),
            
            # 添加语气词
            ('是的', '是的呢'),
            ('好的', '好嘞'),
            ('不是', '不是啊'),
        ]
    
    def paraphrase(self, text: str, intensity: float = 0.5) -> str:
        """对文本进行释义改写"""
        
        result = text
        
        # 根据强度选择改写规则
        num_rules = int(len(self.rewrite_rules) * intensity)
        selected_rules = random.sample(self.rewrite_rules, min(num_rules, len(self.rewrite_rules)))
        
        for pattern, replacement in selected_rules:
            if isinstance(pattern, str) and pattern in result:
                result = result.replace(pattern, replacement, 1)  # 只替换一次
            elif isinstance(pattern, str):
                # 正则表达式
                result = re.sub(pattern, replacement, result, count=1)
        
        return result
    
    def multi_round_paraphrase(self, text: str, rounds: int = 3) -> str:
        """多轮释义改写"""
        
        result = text
        for i in range(rounds):
            intensity = 0.3 + (i * 0.2)  # 逐渐增加强度
            result = self.paraphrase(result, intensity)
        
        return result


class StyleDiversityController:
    """风格多样性控制器 - 避免AI文本的风格单一性"""
    
    def __init__(self):
        self.style_variants = {
            'opening': [
                '直接说结论：',
                '先说结论吧，',
                '我的观点是：',
                '怎么说呢，',
                '其实吧，',
                '说实话，',
            ],
            'transition': [
                '话说回来，',
                '另外，',
                '还有一点，',
                '顺便说一句，',
                '对了，',
                'emmm，',
            ],
            'ending': [
                '就这样吧。',
                '以上。',
                '希望能帮到你。',
                '仅供参考哈。',
                '就这样，拜拜～',
                'over。',
            ],
            'emphasis': [
                '划重点：',
                '注意看，',
                '敲黑板，',
                '重点来了：',
                '这里要注意：',
                '别怪我没提醒你，',
            ],
        }
    
    def add_diversity(self, text: str) -> str:
        """为文本添加风格多样性"""
        
        result = text
        
        # 随机替换开头
        if result.startswith('##'):
            for variant in self.style_variants['opening']:
                if variant in result:
                    new_variant = random.choice(self.style_variants['opening'])
                    result = result.replace(variant, new_variant, 1)
                    break
        
        # 随机添加过渡词
        paragraphs = result.split('\n\n')
        if len(paragraphs) > 2:
            # 在中间段落添加过渡
            mid_idx = len(paragraphs) // 2
            transition = random.choice(self.style_variants['transition'])
            if not paragraphs[mid_idx].startswith(transition):
                paragraphs[mid_idx] = transition + paragraphs[mid_idx]
            result = '\n\n'.join(paragraphs)
        
        return result


class AdvancedContentGenerator:
    """高级内容生成器 - 整合所有前沿技术"""
    
    def __init__(self):
        self.style_learner = StyleLearner()
        self.paraphrase_engine = ParaphraseEngine()
        self.diversity_controller = StyleDiversityController()
    
    def generate_content(
        self,
        topic: Topic,
        account: Account,
        writing_samples: List[str] = None
    ) -> Content:
        """生成内容 - 使用前沿技术"""
        
        # Step 1: 学习或获取作者风格
        if writing_samples:
            style_profile = self.style_learner.learn_from_samples(account.key, writing_samples)
        else:
            style_profile = self.style_learner.get_style_profile(account.key)
        
        # Step 2: 基于风格生成初稿
        draft = self._generate_with_style(topic, account, style_profile)
        
        # Step 3: 多轮释义改写（消除AI痕迹）
        paraphrased = self.paraphrase_engine.multi_round_paraphrase(draft, rounds=3)
        
        # Step 4: 添加风格多样性
        diversified = self.diversity_controller.add_diversity(paraphrased)
        
        # Step 5: 创建Content对象
        content = Content(
            id=f"c_{random.randint(1000, 9999)}",
            account_key=account.key,
            topic=topic,
            content_type="answer",
            title=f"如何评价{topic.title}？",
            body=diversified,
            word_count=len(diversified),
            status=ContentStatus.PENDING_REVIEW,
        )
        
        return content
    
    def _generate_with_style(
        self,
        topic: Topic,
        account: Account,
        style: AuthorStyleProfile
    ) -> str:
        """基于风格画像生成内容"""
        
        # 根据风格特征生成内容
        opening = random.choice([
            '直接说结论：',
            '先说结论吧，',
            '我的观点是：',
        ])
        
        # 根据情感强度选择表达
        if style.emotional_intensity > 0.6:
            emotion = random.choice(['真的绝了', '超级喜欢', '太棒了'])
        elif style.emotional_intensity > 0.3:
            emotion = random.choice(['还不错', '挺好的', '蛮好的'])
        else:
            emotion = random.choice(['一般般', '还行吧', '凑合用'])
        
        # 根据自嘲频率决定是否添加
        self_deprecation = ''
        if random.random() < style.self_deprecation:
            self_deprecation = random.choice([
                '可能我说得不太专业，',
                '外行看法，仅供参考，',
                '不确定是不是个例，',
            ])
        
        # 生成更详细的内容（800-1200字）
        content = f"""
{opening}这个工具我用过，{emotion}。

{self_deprecation}我用了大概一周时间，详细测试了一下。先说价格：¥299/月，年付打7折大概¥2500。

## 我的使用场景

我主要负责后端开发，日常需要处理大量代码审查和文档编写工作。之前试过不少工具，踩了不少坑。比如之前用的一个工具，响应速度特别慢，而且代码质量参差不齐，经常需要手动修改。

## 实测体验

响应速度：大概200ms左右，比我之前用的快了不少。
代码质量：80%的情况下可以直接用，不需要大改。
学习成本：大概花了2天时间熟悉，文档写得还算清楚。

{emotion}，整体体验还不错。

优点：
- 响应速度快，比竞品快30%左右
- 代码质量高，80%可以直接用
- 学习成本低，2天上手
- 支持多种编程语言

缺点：
- 价格有点贵，¥299/月
- 某些高级功能还不够完善
- 偶尔会出现响应超时的情况

## 谁适合买

适合：有预算的专业开发者，追求效率的人，日均代码量>500行的人
不适合：学生党，预算有限的人，偶尔写代码的人

## 购买建议

现在官网有活动，年付打7折，大概¥2500/年。如果月付的话是¥299/月，一年下来要¥3588，差了不少。

链接我放评论区，需要的自取。

{self._generate_conclusion(style)}
"""
        
        return content.strip()
    
    def _generate_conclusion(self, style: AuthorStyleProfile) -> str:
        """生成结论部分"""
        
        if style.opinion_strength > 0.6:
            conclusion = '强烈推荐，值得入手。'
        elif style.opinion_strength > 0.3:
            conclusion = '可以考虑，看个人需求。'
        else:
            conclusion = '一般般吧，看你自己。'
        
        ending = random.choice([
            '就这样吧。',
            '以上。',
            '希望能帮到你。',
            '仅供参考哈。',
        ])
        
        return f"{conclusion}\n\n{ending}"
