# AutoForge Classroom — Devpost Submission Draft

Status: Devpost content updated; only the primary `/feedback` Session ID
remains to be entered.

## Core fields

**Project name:** AutoForge Classroom

**Tagline:** A lesson objective in. A validated classroom video out.

**Track:** Education

**Repository:** https://github.com/junlive0121/autoforge-ai

**Demo video:** https://www.youtube.com/watch?v=ZkelmIA42uU

**Working demo / testing path:** judges should use the provider-free local
Sample Lesson instructions below

**Primary Codex `/feedback` Session ID:** TODO

**License:** MIT

## What it does

Teachers often know exactly what they want students to understand but do not
have hours to script, illustrate, narrate, edit, and quality-check a short
lesson video. AutoForge Classroom turns one lesson objective into a complete
classroom-ready MP4 through a visible multi-agent workflow.

GPT-5.6 Terra acts as the reasoning layer for three structured stages:

1. The Director turns the objective into an audience-aware lesson plan.
2. The Writer creates a concise teaching script.
3. The Storyboard Agent converts the script into inspectable shots with exact
   narration and visual prompts.

OpenAI TTS and DALL-E 3 create narration and frames. A provider-neutral
reliability layer then validates the storyboard and every generated artifact,
derives scene timing from the real narration, assembles the video with FFmpeg,
and verifies that the final MP4 contains valid audio and video streams.

The interface shows every stage, generated frame, failure, and final result.
Judges can use the clearly labeled Sample Lesson path without a live provider
credential; it
exercises the same persistence, media-validation, progress, and FFmpeg assembly
layers with deterministic classroom content.

## Why it matters

The product is aimed at teachers, tutors, and instructional designers who need
short explainers but lack video-production time or specialist tools. The core
idea is not merely AI video generation. It is reliable educational generation:
structured teaching artifacts remain inspectable, failures remain visible, and
invalid or truncated media cannot silently become the final classroom asset.

That makes the workflow easier to trust, review, and adapt than a black-box
"prompt to video" tool.

## How we used GPT-5.6

GPT-5.6 Terra is the default runtime model for planning, writing, and
storyboarding. It is responsible for turning an underspecified lesson objective
into the structured educational decisions that downstream media generation
needs: intended audience, learning objective, narrative structure, exact
narration, visual composition, and shot sequence.

The integration is explicit in `src/config.py` and used by the Director, Writer,
and Storyboard agents. Other models are used only for modality-specific tasks
such as speech and image generation.

## How we used Codex

Codex was the main engineering collaborator during Build Week. It was used to:

- audit the original prototype against the judging and eligibility rules;
- choose the Education positioning and define the public/private code boundary;
- turn reliability patterns into provider-neutral public modules;
- replace in-memory state with atomic, restart-aware project state;
- design shot and media contracts before paid generation begins;
- replace estimated clip timing with real narration duration;
- surface background failures through both WebSocket and polling paths;
- add a deterministic judge-testing path without exposing credentials;
- build and run regression, FFmpeg, path-safety, redaction, and lifecycle tests;
- prepare the submission narrative and demo-video workflow.

Key decisions were reviewed in Codex rather than accepted blindly: the judging
build deliberately excludes SaaS infrastructure and private workstation
integrations, prioritizing a coherent, testable classroom product.

## What existed before Build Week

The pre-existing prototype contained a basic FastAPI application, a general
idea-to-video multi-agent sequence, OpenAI agent wrappers, a simple WebSocket
progress UI, and direct FFmpeg assembly.

## What was added during Build Week

The Build Week work meaningfully extended that prototype with:

- the Education-focused AutoForge Classroom product experience;
- explicit GPT-5.6 Terra integration and documentation;
- storyboard contract validation before media generation;
- decoded-image, audio, intermediate-video, and final-video validation;
- atomic JSON and media publication with path-containment protections;
- durable project state and interrupted-run reconciliation;
- bounded parallel media generation;
- real narration-duration composition and checked FFmpeg diagnostics;
- redacted public errors and reliable WebSocket-to-polling fallback;
- a deterministic Sample Lesson path for judge testing;
- an expanded automated test suite and public-boundary audit.

The dated repository history and the submitted Codex Session ID provide
evidence of these changes during the Submission Period.

## Challenges

The hardest problem was reliability across asynchronous AI and media systems.
A text model can return malformed shot data, a provider can return an HTML error
page where an image was expected, FFmpeg can fail after several expensive calls,
and a browser can lose its WebSocket while the job continues.

We addressed those failures as explicit contracts rather than UI edge cases:
validate before paying for media, publish only validated artifacts, persist
state atomically, expose bounded public errors, and never report completion
until ffprobe confirms the final streams.

## Accomplishments

- A complete lesson-objective-to-video experience rather than a backend-only
  proof of concept.
- Reproducible judge testing without private credentials.
- Real narration timing instead of model-estimated clip duration.
- Failure states that survive browser disconnects and process restarts.
- Provider-neutral safety code with no dependency on the private source project.
- Automated coverage spanning JSON recovery, path safety, state lifecycle,
  media validation, orchestration, and real FFmpeg output.

## What we learned

For educational generation, inspectability matters as much as generation
quality. A teacher needs to see the plan, script, storyboard, and frames—not
only a final black-box video. We also learned that media validity must be treated
as application data integrity: a file existing on disk is not evidence that it
is safe to publish.

## What's next

- curriculum-standard and age-level constraints;
- teacher editing and approval at every structured stage;
- citations and source-grounded lesson generation;
- accessibility controls for captions, reading speed, and visual contrast;
- reusable classroom templates and multilingual lesson variants;
- longitudinal educator feedback on preparation time and revision rate.

## Judge testing instructions

1. Install Python 3.10+ and FFmpeg/ffprobe.
2. Clone the repository.
3. Create and activate a virtual environment.
4. Run `pip install -r requirements.txt`.
5. Set `OPENAI_API_KEY=test-key` when using only the provider-free sample.
6. Start `uvicorn src.main:app --host 127.0.0.1 --port 8000`.
7. Open `http://127.0.0.1:8000`.
8. Click **Try Sample Lesson**.
9. Inspect the plan, script, storyboard, generated frames, and final MP4.

For live generation, provide a valid OpenAI API key and click
**Generate Lesson** instead.

## Final eligibility checklist

- [x] Devpost registration is accepted for the submitting account.
- [x] Education track is selected.
- [x] Every submission field is in English.
- [x] Public repository contains an applicable MIT license.
- [x] README includes setup, testing, Codex decisions, GPT-5.6, and prior/new work.
- [x] Reproducible Sample Lesson instructions are present.
- [x] Demo video is 3:00 or shorter.
- [x] Demo video is uploaded to YouTube as Public.
- [x] Video contains English narration.
- [x] Video shows the working project.
- [x] Video explains specific Codex work and GPT-5.6 integration.
- [ ] Primary `/feedback` Codex Session ID is entered.
- [x] No outstanding team invitations remain.
- [x] Final YouTube link is public and loads successfully.
- [x] Submission remains in the submitted state.
