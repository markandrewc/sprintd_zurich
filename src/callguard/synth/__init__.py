"""Synthetic data kit (v2_plan §4): scenario seeds -> LLM-written Swiss German scripts in the case layout.

- :mod:`callguard.synth.scenarios`: ``config/synth_scenarios.yaml`` (twins per scenario; the expected
  label comes from the scenario, never from the LLM) and the job plan (``Synth_<family>_<nnn>`` ids).
- :mod:`callguard.synth.scripts`: the LLM script writer, its validators and the writer of
  ``data_synth/<set>/{Transkript,Skript_mit_Sollbewertung}/``.

The sets are TEXT ONLY (no audio): ``data.load_calls`` loads them through its text-only path and only
the ORACLE ``reference`` ASR can read them (profile ``config/synth-oracle.yaml``). Evaluate with
``callguard experiment experiments/synth_stress.yaml`` (split ``external``: never a holdout look).
"""
