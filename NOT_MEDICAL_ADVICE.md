# Not Medical Advice

**Cairn is a personal health journal. It is not a medical device, it is not a
clinical decision support tool, and nothing it shows you is medical advice.**

Read this entire document before you install or use Cairn.

## What Cairn is

Cairn is open-source software that lets one person, on their own computer,
record their own self-reported health observations. That includes:

- Body measurements they choose to enter (weight, blood pressure from a home
  cuff, heart rate, etc.)
- Records of when they took their own medications, when they ate, when they
  slept, and how they felt
- Their own answers to validated public-domain self-screening questionnaires
  (PHQ-9, GAD-7, WHO-5, ISI)
- Data their own wearable device generates and that they choose to import

Cairn stores these values in a local SQLite database and in plain-text
markdown files on the user's own computer. It can also display the user's own
historical entries back to them, including simple charts and projections.

## What Cairn is not

Cairn is **not**:

- A medical device, regulated or unregulated, under the U.S. FDA, the
  European MDR, or any other regulatory framework.
- A diagnostic tool, a screening tool, or a triage tool.
- A substitute for examination, evaluation, diagnosis, or treatment by a
  qualified healthcare provider.
- A substitute for an electronic health record (EHR) maintained by a
  healthcare provider.
- A telemedicine, telehealth, or remote patient monitoring product.
- A weight-loss program. Cairn does not prescribe, recommend, or supply diets,
  exercise plans, medications (including GLP-1 receptor agonists such as
  semaglutide or tirzepatide), or any other intervention.
- A mental-health treatment product. The screening questionnaires it
  administers are validated self-report instruments. A score on one of those
  instruments is not a diagnosis, and Cairn does not interpret scores
  clinically.

## The projection feature, specifically

Cairn includes a feature that, based on a user's own historical weight
entries, will draw a simple statistical extrapolation forward in time. **That
projection is a line on a chart, not a forecast, not a goal, and not a
clinical target.** The projection makes no assumptions about diet, exercise,
medication, surgery, or any other intervention. It is bounded by clinically
plausible envelopes solely to prevent the line from leaving the chart, not to
suggest a desirable trajectory.

Do not make medical decisions based on the projection. Do not make medication
decisions based on the projection. Do not make surgical decisions based on
the projection. If a projection appears to "predict" a number on a date,
that prediction is wrong, and Cairn does not represent otherwise.

## GLP-1 receptor agonists, bariatric surgery, and other interventions

Cairn was originally written by an individual managing bariatric surgery
preparation alongside GLP-1 medication therapy. That history is the reason
Cairn exists, and it is also the reason these disclaimers exist.

**Do not start, stop, or adjust the dose of any medication based on what
Cairn shows you.** GLP-1 receptor agonists (including but not limited to
semaglutide, tirzepatide, liraglutide, and dulaglutide) and other weight-loss
or diabetes medications have material side effects, drug interactions, and
contraindications. They require a prescription, supervision by a qualified
prescriber, and ongoing clinical monitoring.

**Do not interpret Cairn's records as a clinical record.** Tell your provider
what you are taking, when you took it, what you ate, and how you feel. Do not
hand them a Cairn export and expect them to treat it as a chart. They cannot
and they should not.

## Mental-health screening instruments

Cairn administers PHQ-9, GAD-7, WHO-5, and ISI to the user, for the user,
about the user. These are validated public-domain self-report instruments.

- A high PHQ-9 score is **not** a diagnosis of major depressive disorder.
- A high GAD-7 score is **not** a diagnosis of generalized anxiety disorder.
- A low WHO-5 score is **not** a diagnosis of any condition.
- A high ISI score is **not** a diagnosis of any sleep disorder.

If you score anywhere that concerns you, **stop and contact a qualified
mental-health professional.** If you are in crisis, call or text 988 (United
States) or the equivalent line in your country. Cairn will not contact anyone
for you. Cairn does not detect crisis. Cairn does not escalate. Cairn is a
record, not a responder.

## No clinical accuracy claims

Cairn makes no claim about the clinical accuracy, validity, sensitivity, or
specificity of the data it records, the calculations it performs, or the
projections it draws. There has been no clinical trial. There has been no
FDA submission. There has been no IRB-approved validation study.

## No "AI-powered" claims as a marketing claim

Some features of Cairn use language models locally on the user's own machine
to format text, summarize entries, or pre-fill forms. Those features do not
practice medicine, do not diagnose, and do not provide clinical
recommendations. The label "AI-powered" is not a substitute for clinical
expertise.

## Use Cairn under the supervision of a healthcare provider

If you have a serious health condition (and bariatric surgery, GLP-1 therapy,
type 2 diabetes, hypertension, heart disease, sleep apnea, depression,
anxiety, and insomnia are all serious health conditions), please:

1. Tell your provider that you are tracking your own observations.
2. Tell them what you are tracking.
3. Take their feedback seriously and adjust what you track based on what
   they tell you matters.
4. Bring questions to them, not to Cairn.

## Reading and accepting these terms

By installing or using Cairn you acknowledge that you have read these
disclaimers and that you accept full responsibility for any decisions you
make about your own health, your own medications, your own diet, your own
exercise, and your own clinical care.

The license under which Cairn is distributed (Apache License 2.0) **includes
a disclaimer of warranty and a limitation of liability**. Read those terms in
[LICENSE](LICENSE). The author of Cairn provides this software "AS IS" and
disclaims all warranties, express or implied, to the maximum extent permitted
by law.

If you do not accept these terms, do not install or use Cairn.
