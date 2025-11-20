# Evaluation Verification

Automatic verification that runs after evaluation to ensure quality and consistency.

## Overview

Verification automatically checks completed evaluations against 4 criteria:

1. **Rubric Compliance** - All rubric criteria are scored
2. **JSON Validity** - All evaluation data is valid and complete
3. **No Hallucination** - Scores appropriately reflect available information
4. **Consistency** - Score distribution is reasonable

The verification runs **automatically in Step 7** after evaluation completes.



### Files

- `post_evaluation_verifier.py` - Main verification module
- `README.md` - This documentation

## Usage

### Automatic (Recommended)
```bash
python run_pipeline.py
```
Verification runs automatically as Step 7 after evaluation.

### Manual
```bash
python verification/post_evaluation_verifier.py
```
Run verification anytime on existing evaluations.

## Verification Checks

### Check 1: Rubric Compliance
**What it checks:**
- All rubric criteria are present in each evaluation
- No missing criteria across all completed evaluations

**Pass criteria:**
- Every evaluation has all expected rubric criteria scored

**Example output:**
```
✅ All evaluations have complete rubric criteria
   Expected criteria: clarity, novelty, evidence, feasibility, long_term_value, security_compliance
```

---

### Check 2: JSON Validity
**What it checks:**
- All evaluation data is valid JSON
- Required fields are present and not null
- Data types are correct

**Pass criteria:**
- All evaluations have valid JSON structure
- No null values in required fields

**Required fields:**
- `evaluation_scores` (JSON object)
- `weighted_total_score` (number)
- `investment_recommendation` (string)
- `key_strengths` (array)
- `key_concerns` (array)

**Example output:**
```
✅ All evaluations have valid JSON structure
   Required fields: scores, weighted_total, recommendation, strengths, concerns
```

---

### Check 3: No Hallucination
**What it checks:**
- Ideas with minimal information don't have suspiciously high scores
- Scores reflect the quality and quantity of available information
- `insufficient_info` flag is used appropriately

**Pass criteria:**
- No high scores (>7) for ideas with minimal information
- Or `insufficient_info` flag is set when appropriate

**Example output:**
```
✅ No obvious hallucination detected
   Scores appropriately reflect available information
```

---

### Check 4: Consistency
**What it checks:**
- Score distribution across all evaluations
- Scores are neither too similar nor too different
- Reasonable spread indicates proper discrimination

**Pass criteria:**
- Score range between 0.5 and 9.0
- Reasonable distribution

**Example output:**
```
✅ Score distribution looks reasonable
   Average: 6.94
   Range: 6.66 - 7.50
   Spread: 0.84
```

---

## Interpreting Results

### All Checks Pass ✅
```
Evaluated Ideas: 4
Verification Checks: 4/4 passed (100%)

🎉 All verification checks passed!
✅ Evaluation quality is good!
```
**Meaning**: All evaluations are high quality and ready to use

**Action**: Proceed with confidence

---

### 3/4 Checks Pass ✅
```
Evaluated Ideas: 4
Verification Checks: 3/4 passed (75%)

✅ 3/4 checks passed - Evaluation quality is acceptable
⚠️  2 warnings detected
```
**Meaning**: Evaluations are acceptable with minor issues

**Action**: Review warnings but generally safe to proceed

---

### 2/4 Checks Pass ⚠️
```
Evaluated Ideas: 4
Verification Checks: 2/4 passed (50%)

❌ Only 2/4 checks passed - Review evaluation quality
```
**Meaning**: Significant quality issues detected

**Action**: Review failed checks and consider re-evaluation

---

### Less Than 2 Checks Pass ❌
```
Evaluated Ideas: 4
Verification Checks: 1/4 passed (25%)

❌ Only 1/4 checks passed - Review evaluation quality
```
**Meaning**: Major quality problems

**Action**: Do not use evaluations - investigate and fix issues

### Common Issues and Solutions

#### Missing Rubric Criteria
**Symptom**: Some evaluations missing certain criteria
**Cause**: LLM skipped criteria or database update failed
**Solution**: Re-run evaluation for affected ideas

#### Invalid JSON
**Symptom**: JSON parsing errors in evaluation data
**Cause**: LLM output formatting issues or database corruption
**Solution**: Check evaluation_scores field, re-evaluate if needed

#### Hallucination Warnings
**Symptom**: High scores for ideas with minimal information
**Cause**: LLM being too generous or not using insufficient_info flag
**Solution**: Review prompt to emphasize conservative scoring for limited data

#### Narrow Score Range
**Symptom**: All scores very similar (range < 0.5)
**Cause**: Lack of discrimination between ideas
**Solution**: Review rubric weights and evaluation criteria

#### Wide Score Range
**Symptom**: Scores too spread out (range > 9.0)
**Cause**: Inconsistent evaluation standards
**Solution**: Review evaluation consistency, check for outliers

## Best Practices

### Running Evaluations
1. Always run the full pipeline with `python run_pipeline.py`
2. Verification runs automatically after evaluation
3. Review verification output before using results
4. Address any warnings or failures immediately

### Monitoring Quality
1. Check verification results after each pipeline run
2. Track pass rates over time
3. Investigate any sudden changes in verification results
4. Keep logs of verification warnings

### After Changes
1. Re-run pipeline after rubric changes
2. Re-run after prompt modifications
3. Compare verification results before/after changes
4. Ensure all checks still pass

## Troubleshooting

### No Evaluations Found
```
⚠️  No completed evaluations found. Skipping verification.
```
**Solution**: Run evaluations first with `python run_pipeline.py`

### Missing Criteria
```
❌ 2 evaluations have missing criteria
```
**Solution**: 
1. Check which ideas are affected in warnings
2. Re-run evaluation for those specific ideas
3. Verify rubrics table has correct criteria

### Invalid JSON
```
❌ 1 evaluations have invalid JSON
```
**Solution**:
1. Check the evaluation_scores field in database
2. Look for malformed JSON
3. Re-evaluate the affected idea

### Database Connection Error
```
❌ Error: connection refused
```
**Solution**: 
1. Ensure PostgreSQL is running
2. Check DB_CONFIG in config/config.py
3. Verify database exists

## Example Output

Here's what you'll see when verification runs:

```
================================================================================
🔍 POST-EVALUATION VERIFICATION
================================================================================

📊 Found 4 completed evaluations

================================================================================
CHECK 1: Rubric Compliance
================================================================================

✅ All evaluations have complete rubric criteria
   Expected criteria: clarity, novelty, evidence, feasibility, long_term_value, security_compliance

================================================================================
CHECK 2: JSON Validity
================================================================================

✅ All evaluations have valid JSON structure
   Required fields: scores, weighted_total, recommendation, strengths, concerns

================================================================================
CHECK 3: No Hallucination
================================================================================

✅ No obvious hallucination detected
   Scores appropriately reflect available information

================================================================================
CHECK 4: Consistency
================================================================================

✅ Score distribution looks reasonable
   Average: 6.94
   Range: 6.66 - 7.50
   Spread: 0.84

================================================================================
📊 VERIFICATION SUMMARY
================================================================================

Evaluated Ideas: 4
Verification Checks: 4/4 passed (100%)

🎉 All verification checks passed!
✅ Evaluation quality is good!

================================================================================
```


