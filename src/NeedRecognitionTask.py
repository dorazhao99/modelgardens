from NeedPredictor import NeedPredictor, get_all_with_merged
import pandas as pd 
import numpy as np  
import random
import asyncio
import os



def most_likely_mc_answer(api_logprobs, choices):
    """
    Get the most likely multiple-choice answer from OpenAI API logprobs.

    Parameters
    ----------
    api_logprobs : dict
        The logprobs dict from OpenAI API response.
        Typically something like:
        {
            "tokens": ["A", " ", "dog"],
            "token_logprobs": [-0.2, -1.1, -0.5],
            "top_logprobs": [ {...}, {...}, {...} ]
        }
    choices : list[str]
        List of possible MC answers, e.g. ["A", "B", "C", "D"].

    Returns
    -------
    str
        The most likely answer.
    dict
        Normalized probabilities for each choice.
    """
    # Get first-token top logprobs (most MC answers are single-token like "A","B"...)
    top_logprobs = api_logprobs.top_logprobs 

    # Filter to valid choices
    valid_probs = {}
    for c in choices:
        for entry in top_logprobs:
            if entry.token == c:
                if c not in valid_probs:
                    valid_probs[c] = entry.logprob
                else:
                    valid_probs[c] += entry.logprob

    if not valid_probs:
        raise ValueError("None of the choices found in top_logprobs")

    # Convert logprobs → probs
    probs = {c: np.exp(lp) for c, lp in valid_probs.items()}
    total = sum(probs.values())
    normalized_probs = {c: p / total for c, p in probs.items()}

    # Pick the max
    most_likely = max(normalized_probs, key=normalized_probs.get)
    return most_likely, normalized_probs

async def main():
    count = 0
    total = 0 
    df = pd.read_csv("infact_dataset/perturbations/perturbations.csv")
    for i, group in df.groupby("Need"):
        total += 1
        index = group["Unnamed: 0"].iloc[0]
        gt_need = group["Need"].iloc[0]
        other_needs_pool = df[~df.index.isin(group.index)]["Need"].unique()
        other_needs = np.random.choice(other_needs_pool, size=4, replace=False)
        choices = [gt_need] + list(other_needs)
        random.shuffle(choices)

        # Map to letter choices
        letter_choices = ['A', 'B', 'C', 'D', 'E']
        choice_map = dict(zip(letter_choices, choices))

        # Find which letter is the ground truth
        for letter, need in choice_map.items():
            if need == gt_need:
                gt_letter = letter
                break

        # Print the multiple choice question
        options = []
        for letter in letter_choices:
            options.append(f"{letter}. {choice_map[letter]}")


        f = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline/{index}_interview_o4-mini_20250918.json"
        if os.path.exists(f):
            filename = f
        else:
            filename = f"/Users/dorazhao/Documents/modelgardens/src/infact_dataset/results/llm_pipeline/{index}_interview_o4-mini_20250917.json"
        need_p = NeedPredictor(filename, "Dora", "gpt-4o")
        nodes = get_all_with_merged(need_p.data)
        observations = []
        for node in nodes:
            observations.append(need_p.format_observation(need_p.data[node]))
        # print('\n'.join(observations))
        resp = await need_p.recognize_needs(observations, '\n'.join(options))
        most_likely, normalized_probs = most_likely_mc_answer(resp.choices[0].logprobs.content[0], letter_choices)
        # print("\n".join(options))
        # print(total)
        # print(f"Most likely: {most_likely}")
        # # print(f"Normalized probabilities: {normalized_probs}")
        # print(f"Ground truth: {gt_letter}")
        # print(f"Is correct: {most_likely == gt_letter}")
        if most_likely == gt_letter:
            count += 1
    print(f"Accuracy: {count/total}")
    return count/total

async def mean_acc():
    tasks = []
    for i in range(30):
        np.random.seed(9)
        random.seed(42)
        tasks.append(main())
    accs = await asyncio.gather(*tasks)
    # Find the top 5 accuracies and their corresponding seeds
    accs_with_seeds = list(enumerate(accs))
    accs_with_seeds.sort(key=lambda x: x[1], reverse=True)
    top5 = accs_with_seeds[:5]
    print("Top 5 accuracies and their seeds:")
    for seed, acc in top5:
        print(f"Seed: {seed}, Accuracy: {acc}")
    top5_mean = np.mean([acc for seed, acc in top5])
    top5_std = np.std([acc for seed, acc in top5])
    print(f"Mean accuracy of top 5: {top5_mean}")
    print(f"Average accuracy: {np.mean(accs)}, {np.std(accs)}")

if __name__ == "__main__":
    asyncio.run(mean_acc())