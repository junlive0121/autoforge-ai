# AutoForge Classroom — Demo Video Script

Target duration: 2:40–2:55
Language: English
Format: 1920×1080, H.264/AAC, public YouTube video

## 0:00–0:14 — Problem and promise

**Visual:** Product title, then the lesson-objective input.

**Narration:**

> Teachers know what students need to learn, but producing one polished lesson
> video can take hours. AutoForge Classroom turns a single lesson objective into
> a planned, narrated, illustrated, and validated classroom video.

## 0:14–0:42 — Working product

**Visual:** Enter “Explain photosynthesis to middle-school students” and click
Try Sample Lesson. Show the five progress stages.

**Narration:**

> I can enter a learning objective and follow the complete workflow. The
> Director creates an audience-aware teaching plan. The Writer creates the
> script. The Storyboard Agent creates exact narration and visual instructions.
> The media and assembly stages then produce the final MP4.

## 0:42–1:08 — Inspectable educational artifacts

**Visual:** Show the plan, script, storyboard JSON, and generated frame gallery.

**Narration:**

> This is deliberately not a black box. A teacher can inspect the learning
> objective, explanation structure, narration, shot order, and every generated
> frame. The sample path is deterministic and provider-free for judge testing,
> while exercising the same persistence, validation, progress, and FFmpeg
> layers as live generation.

## 1:08–1:30 — Final video

**Visual:** Play several seconds of the generated photosynthesis video.

**Narration:**

> The final lesson uses the real narration duration, so speech is not clipped by
> a model estimate. Before the result is published, AutoForge verifies that the
> images decode correctly and that the final file contains valid audio and video
> streams.

## 1:30–1:55 — GPT-5.6

**Visual:** Show `src/config.py`, followed by the Director, Writer, and
Storyboard agent calls.

**Narration:**

> GPT-5.6 Terra is the reasoning layer for the live workflow. It turns an
> underspecified lesson objective into structured decisions about audience,
> learning objective, teaching sequence, narration, visual composition, and
> shot order. Its outputs are validated before expensive media generation
> begins.

## 1:55–2:25 — Codex collaboration

**Visual:** Briefly show the primary Codex task, then the reliability modules
and test output.

**Narration:**

> Codex was my main Build Week engineering collaborator. I used it to audit the
> original prototype, choose the Education focus, define the public code
> boundary, implement atomic project state and media publication, correct
> narration timing, surface background failures, and build regression tests.
> The most important decision was to prioritize a coherent, testable classroom
> product instead of adding unrelated SaaS infrastructure.

## 2:25–2:44 — Reliability proof

**Visual:** Show `27 passed`, the media-validation module, and the durable
project JSON.

**Narration:**

> The result is a non-trivial pipeline that treats generated media as data
> integrity. Invalid storyboards stop early, failed downloads cannot masquerade
> as images, interrupted jobs remain visible, and FFmpeg failure can never be
> reported as success.

## 2:44–2:55 — Close

**Visual:** Product logo and final video gallery.

**Narration:**

> AutoForge Classroom gives educators a faster path from teaching intent to a
> reviewable classroom asset. A lesson objective in; a validated lesson video
> out.

## Recording checklist

- Record at 1920×1080 or 1440×900 with browser zoom adjusted for readability.
- Hide API keys, local user paths, notifications, and unrelated browser tabs.
- Keep the Sample Lesson label visible so the deterministic path is not
  misrepresented as a live provider call.
- Show the project running, not only slides.
- Show the Codex task briefly if no sensitive conversation is visible.
- Replace “27 passed” if the final test count changes.
- Keep the final export below 3:00.
