# Topic-Neutral Headline Representation Prompt v1

## Purpose

Create content representations for story clustering without using market
outcomes and without allowing positive or negative tone to determine clusters.

## Prompt

You are preparing financial-news headlines for outcome-blind topic and story
clustering. For every supplied item, use only its `record_id` and `headline`.
Do not browse, retrieve the article, infer its source or date, predict the
market, assign sentiment, or use knowledge of subsequent events.

Return one JSON object with an `items` array. Preserve every `record_id`. Each
item must contain exactly:

```json
{
  "record_id": "unchanged input ID",
  "topic_neutral_text": "one concise neutral description",
  "entities": ["named actors, institutions, places, assets, or policies"],
  "event_terms": ["concrete actions or information objects"]
}
```

Rules for `topic_neutral_text`:

1. Preserve who or what the headline concerns and what happened or may happen.
2. Preserve event identity, policy question, asset, location, and named actors.
3. Remove bullish, bearish, alarming, reassuring, celebratory, or condemnatory
   framing unless that framing is itself the reported event.
4. Replace descriptions of market direction with a neutral description of the
   market reaction when direction is not needed to identify the story.
5. Do not add facts absent from the headline.
6. Do not decide whether two headlines belong together.
7. Keep the description under 30 words.

Return valid JSON only.
