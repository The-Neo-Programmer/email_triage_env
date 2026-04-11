import json
import re
from typing import Dict, List, Any

# Hackathon validator requirement: task scores must be strictly within (0, 1).
# We clamp all grader outputs into the open interval using a tiny epsilon.
_EPS = 1e-6


def _clamp_open01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        x = 0.0
    if x <= 0.0:
        return _EPS
    if x >= 1.0:
        return 1.0 - _EPS
    return x

class TriageGraders:
    @staticmethod
    def grade_classify(predicted: Dict[str, str], ground_truth: Dict[str, Any]) -> float:
        """
        Grades Task 1 (Classify).
        Scores urgency and category. Total max 1.0.
        """
        score = 0.0
        
        # Check urgency
        pred_urgency = str(predicted.get("urgency", "")).lower().strip()
        gt_urgency = str(ground_truth.get("urgency", "")).lower().strip()
        
        if pred_urgency == gt_urgency:
            score += 0.5
        elif (pred_urgency in ["high", "critical"] and gt_urgency in ["high", "critical"]) or \
             (pred_urgency in ["low", "medium"] and gt_urgency in ["low", "medium"]):
            score += 0.25 # Partial credit for being in the right ballpark
            
        # Check category
        pred_category = str(predicted.get("category", "")).lower().strip()
        gt_category = str(ground_truth.get("category", "")).lower().strip()
        
        if pred_category == gt_category:
            score += 0.5
            
        return _clamp_open01(min(max(score, 0.0), 1.0))
        
    @staticmethod
    def grade_extract(predicted: Dict[str, List[str]], ground_truth: Dict[str, Any]) -> float:
        """
        Grades Task 2 (Extract).
        Returns F1-like score based on word overlap of action items.
        """
        pred_actions = predicted.get("action_items", [])
        if not isinstance(pred_actions, list):
            return _clamp_open01(0.0)
            
        gt_actions = ground_truth.get("action_items", [])
        
        if not gt_actions and not pred_actions:
            return _clamp_open01(1.0) # Correctly identified no action items
            
        if not gt_actions and pred_actions:
            return _clamp_open01(0.0) # Hallucinated action items
            
        if not pred_actions and gt_actions:
            return _clamp_open01(0.0) # Missed action items
            
        def normalize(text):
            return set(re.findall(r'\b\w+\b', str(text).lower()))
            
        gt_words = [normalize(a) for a in gt_actions]
        pred_words = [normalize(a) for a in pred_actions]
        
        total_score = 0.0
        # For each ground truth action, find the best matching predicted action
        for gt_set in gt_words:
            best_match_score = 0.0
            for pred_set in pred_words:
                if not pred_set or not gt_set:
                    continue
                intersection = len(gt_set.intersection(pred_set))
                union = len(gt_set.union(pred_set))
                jaccard = intersection / union
                if jaccard > best_match_score:
                    best_match_score = jaccard
            total_score += best_match_score
            
        # Add penalty for hallucinated extra action items
        precision_penalty = max(0, (len(pred_actions) - len(gt_actions)) * 0.1)
        
        final_score = (total_score / len(gt_actions)) - precision_penalty
        return _clamp_open01(min(max(final_score, 0.0), 1.0))
        
    @staticmethod
    def grade_respond(predicted_responseText: str, ground_truth: Dict[str, Any]) -> float:
        """
        Grades Task 3 (Respond).
        Hybrid grading: 40% programmatic, 60% LLM based on professionalism, coverage, and policy compliance.
        """
        text = str(predicted_responseText).strip()
        if not text:
            return _clamp_open01(0.0)
            
        score = 0.0
        
        # --- 40% Programmatic ---
        # Word count check (between 5 and 250 words)
        words = text.split()
        if 5 <= len(words) <= 250:
            score += 0.2
            
        # Greeting/Sign-off check
        lower_text = text.lower()
        has_greeting = any(g in lower_text[:50] for g in ["hi", "hello", "dear", "thanks", "hey"])
        has_signoff = any(s in lower_text[-100:] for s in ["best", "regards", "sincerely", "thanks", "cheers"])
        
        if has_greeting:
            score += 0.1
        if has_signoff:
            score += 0.1
            
        # --- 60% LLM Component ---
        llm_score = 0.0
        try:
            import os
            from openai import OpenAI
            import json
            
            hf_token = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
            if hf_token:
                client = OpenAI(
                    base_url="https://router.huggingface.co/v1",
                    api_key=hf_token
                )
                
                system_prompt = (
                    "You are an expert AI evaluator assessing an email response drafted by an agent. "
                    "You must output only a JSON object containing three integer scores between 0 and 5:\n"
                    "1. professionalism: Tone and appropriateness.\n"
                    "2. coverage: Did it address the required keywords and action items?\n"
                    "3. compliance: Does it follow internal policy (e.g. not processing fraudulent wire transfers)?\n"
                    "Format: {\"professionalism\": 5, \"coverage\": 5, \"compliance\": 5}"
                )
                
                expected_keywords = ground_truth.get("ideal_response_keywords", [])
                user_prompt = f"Expected keywords/topics: {expected_keywords}\n\nDrafted Email:\n{text}\n\nEvaluate the email and return the JSON."
                
                completion = client.chat.completions.create(
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=100
                )
                
                content = completion.choices[0].message.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.replace("```", "").strip()
                    
                result = json.loads(content)
                p = int(result.get("professionalism", 0))
                cov = int(result.get("coverage", 0))
                comp = int(result.get("compliance", 0))
                
                # Max sum is 15. Map 15 to 0.6
                total_llm = p + cov + comp
                llm_score = (total_llm / 15.0) * 0.6
            else:
                # Fallback to the old keyword matching if no API key is provided
                keywords = ground_truth.get("ideal_response_keywords", [])
                if not keywords:
                    if len(words) < 20: 
                        llm_score += 0.6
                else:
                    keyword_score = sum(1 for kw in keywords if kw.lower() in lower_text) / len(keywords)
                    llm_score += (keyword_score * 0.6)
        except Exception as e:
            # Fallback on error
            keywords = ground_truth.get("ideal_response_keywords", [])
            if not keywords:
                if len(words) < 20: 
                    llm_score += 0.6
            else:
                keyword_score = sum(1 for kw in keywords if kw.lower() in lower_text) / len(keywords)
                llm_score += (keyword_score * 0.6)
                
        score += llm_score
            
        return _clamp_open01(min(max(score, 0.0), 1.0))
