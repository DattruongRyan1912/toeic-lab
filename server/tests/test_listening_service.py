import pytest
from server.services import listening_service


def test_phonetic_cues_detection():
    # Flap-T detection
    cues_water = listening_service.detect_phonetic_cues("The water in the bottle is cold.")
    assert any("Flap-T" in c for c in cues_water)

    # Consonant to vowel linking
    cues_link = listening_service.detect_phonetic_cues("Please check out of the room.")
    assert any("Nối âm" in c for c in cues_link)

    # Elision
    cues_elision = listening_service.detect_phonetic_cues("He was here last night.")
    assert any("Nuốt âm" in c for c in cues_elision)


def test_diff_transcription():
    # Exact match
    res_exact = listening_service.diff_transcription(
        learner_text="They're discussing the project schedule.",
        target_transcript="They're discussing the project schedule."
    )
    assert res_exact["accuracy"] == 100.0
    assert all(t["status"] == "correct" for t in res_exact["tokens"])

    # Typos and omissions
    res_diff = listening_service.diff_transcription(
        learner_text="The repo will be finish tomorow",
        target_transcript="The report will be finished tomorrow."
    )
    assert res_diff["accuracy"] < 100.0
    assert any(t["status"] in ("misspelled", "missing") for t in res_diff["tokens"])


def test_listening_api_endpoints(client, seeded):
    # Check exercises list
    resp = client.get("/api/listening/exercises")
    assert resp.status_code == 200
    exercises = resp.json()
    assert isinstance(exercises, list)
    assert len(exercises) > 0

    first_id = exercises[0]["id"]

    # Check dictation diff API
    check_payload = {
        "question_id": first_id,
        "learner_text": "They are working on the project."
    }
    resp_check = client.post("/api/listening/check-dictation", json=check_payload)
    assert resp_check.status_code == 200
    data = resp_check.json()
    assert "accuracy" in data
    assert "tokens" in data
    assert "phonetic_cues" in data

    # Check activity tracking
    track_payload = {
        "mode": "dictation",
        "seconds": 45,
        "items": 1
    }
    resp_track = client.post("/api/listening/track", json=track_payload)
    assert resp_track.status_code == 200
    assert resp_track.json()["status"] == "tracked"
