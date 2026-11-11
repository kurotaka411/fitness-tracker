from scripts.import_foods import parse_value

def new_counts():
    return {"括弧付き": 0, "Tr": 0, "-": 0}

def test_parse_paren():
    counts = new_counts()

    result = parse_value("(11.3)", counts)
    assert result == 11.3
    assert counts["括弧付き"] == 1

def test_parse_number():
    counts = new_counts()

    result = parse_value(12.5, counts)
    assert result == 12.5 
    assert counts == {"括弧付き": 0, "Tr": 0, "-": 0}

def test_parse_tr():
    counts = new_counts()
    result = parse_value("Tr", counts)
    assert result == 0.0
    assert counts["Tr"] == 1

def test_parse_paren_tr():
    counts = new_counts()
    result = parse_value("(Tr)", counts)
    assert result == 0.0
    assert counts["括弧付き"] == 1

def test_parse_dash():
    counts = new_counts()
    result = parse_value("-", counts)
    assert result is None
    assert counts["-"] == 1