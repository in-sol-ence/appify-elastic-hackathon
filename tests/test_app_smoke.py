from streamlit.testing.v1 import AppTest


def test_app_starts_without_exception() -> None:
    app = AppTest.from_file("app.py", default_timeout=15)
    app.run()
    assert not app.exception
    assert app.title[0].value == "Robotics BOM Guardian"
    wizard = app.session_state["wizard_state"]
    assert wizard.project is not None
    assert wizard.project_id is None
    assert wizard.current_step == 1
    assert wizard.persistence_status in {"unsaved", "error"}
