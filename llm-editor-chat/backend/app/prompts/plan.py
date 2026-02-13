# making plan for document creation
import re
from typing import Dict, Tuple

# 高质量文档写作，是一个“需求→策划→结构→打磨→反馈→输出”的系统工程。每个步骤都要“再深入一层”，而不是表面处理。
class PlanPrompts:
    """
    Static method class containing prompts for planning content creation.
    """

    # 计划的基本流程
    def __init__(self):
        """
        Initializes the PlanPrompts class.
        """
        pass


    # 计划的主要信息提取step1a，gpt 4.1，no thinking audience & Concerns + Decisive Parameters-part1
    def plan_audience_baseline_extractor(input_str):
        """
        Returns the prompt for defining the target audience for content creation.

        Returns:
            str: The plan target audience prompt
        """
        return f"""
        Extract metadata from material, return JSON only:
        <Material>
        {input_str}
        </Material>
```json
{
  "Document type": "≤10 chars (English)",
  "Purpose": "≤40 chars",
  "Target audience": ["≤20 chars", …],
  "Expected length": "≤20 chars",
  "Top concerns (by priority)": ["≤30 chars", …],
  "Tone": "Formal|Professional|Conversational|Friendly|Playful",
  "CTA": "≤40 chars",
  "Topic complexity": "Low|Medium|High",
  "Missing info": ["≤30 chars", …]
}
```
Rules:
1. "Document type" in English, rest match input language
2. Unknown = "TBC"
3. Empty lists = []
4. Respect character limits
5. Keep key order
6. JSON only, no commentary
        """

    # 计划的高级参数提取，step2b
    @staticmethod
    def plan_advanced_parameter_extractor(input_str: str):
        """
        Returns the prompt for extracting decisive parameters for content creation.

        Returns:
            str: The plan decisive parameters prompt
        """
        return f"""
Extract advanced writing constraints from material, return JSON only:
<Material>
{input_str}
</Material>
```json
{
  "Structure / format norms": "≤40 chars or []",
  "Citation accuracy": "High|Medium|Low|TBC",
  "Industry / compliance constraints": ["≤30 chars", …],
  "Style focus": "Literary‑flair|Data‑driven|Story‑telling|Minimalistic|TBC"
}
```
Rules:
1. Match input language
2. Unknown = "TBC" (or [] for arrays)
3. Respect character limits
4. Keep key order
5. JSON only
"""

    # 判断是否要提取高级参数
    @staticmethod
    def needs_step2b(step2a: Dict, raw_brief: str) -> Tuple[bool, str]:
        """
        Decide whether to invoke Step 2b (advanced‑constraint extractor).

        Parameters
        ----------
        step2a : dict
            Parsed JSON from Step 2a, already loaded into a Python dict.
        raw_brief : str
            The original user brief in plain text.

        Returns
        -------
        Tuple[bool, str]
            (True/False, "reason code")  – `reason code` is the first rule that fired.
            If no rule fires, returns (False, "none").
        """

        # ---------- Gate A: Document‑type gate ----------
        doc_type_advanced = step2a.get("Document type", "").lower() in {
            "whitepaper", "report", "manual", "policy", "paper",
            "agreement", "api-doc", "api", "sop", "slide", "deck"
        }
        if doc_type_advanced:
            return True, "A_doc_type"

        # ---------- Gate B: Length‑&‑complexity gate ----------
        expected_len = step2a.get("Expected length", "").lower()
        topic_complex = step2a.get("Topic complexity", "").lower()

        long_doc = (
                re.search(r"(>|≈|about|approx|至少|大于|\d+)\s*(pages?|页|words?|字)", expected_len)
                and not re.search(r"(<=|≤|<|不到|少于)", expected_len)
        )
        high_complex = topic_complex.startswith("high")

        if long_doc and high_complex:
            return True, "B_len_complex"

        # ---------- Gate C: Audience / purpose gate ----------
        audience_keywords = {"regulator", "legal", "investor", "academic", "审计", "监管", "法律",
                             "投"}  # Chinese + English
        purpose_keywords = {"publish", "compliance", "funding", "上市", "融资", "合规"}

        audience_hit = any(k.lower() in " ".join(step2a.get("Target audience", [])).lower()
                           for k in audience_keywords)
        purpose_hit = any(k in step2a.get("Purpose", "").lower()
                          for k in purpose_keywords)

        if audience_hit or purpose_hit:
            return True, "C_audience_purpose"

        # ---------- Gate D: Keyword heuristics in brief ----------
        if re.search(r"\b(APA|IEEE|GB/T|Chicago|GDPR|HIPAA|FINRA|ISO|Markdown|LaTeX|PPT|PowerPoint)\b",
                     raw_brief, flags=re.I):
            return True, "D_keyword"

        # ---------- Gate E: TBC / missing critical fields ----------
        tbc_fields = {"Expected length", "Topic complexity", "Tone", "CTA"}
        if any(step2a.get(field) == "TBC" for field in tbc_fields):
            return True, "E_TBC"

        return False, "none"

    # 计划的核心卖点：AI分析，现有核心卖点，再有评分标准, gpt-4.1-mini is ok
    @staticmethod
    def plan_sell_points_prompt(input_str: str, target_audience: str):
        """
        Returns the prompt for planning content creation.

        Returns:
            str: The plan content creation prompt
        """
        return f"""
**Task**  
You are a senior content-strategy consultant. Extract the most persuasive selling points that match the audience’s main concerns.

<OriginalBrief>
{input_str}
</OriginalBrief>

<TargetAudience>
{target_audience}
</TargetAudience>

**Output**  
1. **Selling-Point Matrix (Markdown)**  
   | Concern | Have | Need | Draft Point (≤30 chars) |  
2. **<SellingPoints>**  
   - 3–5 bullet points, ≤20 words each, quantify when possible.  
   </SellingPoints>

**Self-Check (hide from user)**  
- ≥80 % concern coverage  

Return only the specified content as plain text, in number list.
"""

    # 计划的评分标准，gpt-o3
    @staticmethod
    def plan_scoring_criteria_prompt(baseline_json: dict, advanced_json_or_none: dict, selling_points: str):
        """
        Returns the prompt for planning scoring criteria for content creation.

        Returns:
            str: The plan scoring criteria prompt
        """
        return f"""
**ROLE: system**
You are a "Directive Composer." Generate Key Writing Directives from metadata to guide GPT-Writer.

**ROLE: user**
<BaselineInfo>{baseline_json}</BaselineInfo>
<AdvancedInfo>{advanced_json_or_none}</AdvancedInfo>
<CoreSellingPoints>{selling_points}</CoreSellingPoints>

**Output:**
1. Use `Preferred language` (fallback: brief language)
2. Plain text, no Markdown/JSON
3. Numbered list titled "Key Writing Directives"
4. Include bullets (omit if missing/none):
   ① Cover concerns: [Top concerns]
   ② Highlight USPs: [CoreSellingPoints]
   ③ Length/structure: [Expected length]; [Structure norms]
   ④ Citations: ≥[min_cites] sources, [Citation accuracy]
   ⑤ Compliance: [Industry constraints]
   ⑥ Tone/style: [Tone]; [Style focus]
   ⑦ End with CTA: "[CTA]"

5. ≤120 chars per bullet, max 8 bullets
6. Output only the numbered list
"""