from mobile_rag.environment import openrouter_api_key


def test_key_precedence_and_template_not_loaded(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    package = tmp_path / "src/mobile_rag"
    package.mkdir(parents=True)
    (package / ".env.example").write_text("OPENROUTER_API_KEY=template", encoding="utf-8")
    assert openrouter_api_key(tmp_path) is None
    (package / ".env").write_text('OPENROUTER_API_KEY="package-test"\n', encoding="utf-8-sig")
    assert openrouter_api_key(tmp_path) == "package-test"
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=root-test\n", encoding="utf-8")
    assert openrouter_api_key(tmp_path) == "root-test"
    monkeypatch.setenv("OPENROUTER_API_KEY", "process-test")
    assert openrouter_api_key(tmp_path) == "process-test"
