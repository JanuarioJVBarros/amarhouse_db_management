from openpyxl import Workbook

from scripts.update_prices import load_prices_from_excel, update_prices_from_map


class StubVariantsAPI:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.updates = []

    def update_variant(self, **kwargs):
        if self.should_fail:
            raise RuntimeError("update failed")
        self.updates.append(kwargs)


def create_price_workbook(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["REF", "Preço Loja c/ IVA 23% (€)"])

    for row in rows:
        sheet.append(row)

    workbook.save(path)


def test_load_prices_from_excel_reads_and_normalizes_values(tmp_path):
    file_path = tmp_path / "prices.xlsx"
    create_price_workbook(
        file_path,
        [
            [" abc-1 ", "12,50 €"],
            ["xyz-2", 3.75],
        ],
    )

    result = load_prices_from_excel(file_path)

    assert result == {"ABC-1": 12.5, "XYZ-2": 3.75}


def test_load_prices_from_excel_skips_excel_error_values(tmp_path, capsys):
    file_path = tmp_path / "prices_with_errors.xlsx"
    create_price_workbook(
        file_path,
        [
            ["abc-1", "#VALUE!"],
            ["xyz-2", "5,00 â‚¬"],
        ],
    )

    result = load_prices_from_excel(file_path)

    assert result == {"XYZ-2": 5.0}
    output = capsys.readouterr().out
    assert "[SKIP] Invalid price for ABC-1: #VALUE!" in output


def test_load_prices_from_excel_skips_div_zero_values(tmp_path, capsys):
    file_path = tmp_path / "prices_with_div_zero.xlsx"
    create_price_workbook(
        file_path,
        [
            ["abc-1", "#DIV/0!"],
            ["xyz-2", "5,00 €"],
        ],
    )

    result = load_prices_from_excel(file_path)

    assert result == {"XYZ-2": 5.0}
    output = capsys.readouterr().out
    assert "[SKIP] Invalid price for ABC-1: #DIV/0!" in output


def test_load_prices_from_excel_raises_for_missing_headers(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["WRONG", "HEADERS"])
    file_path = tmp_path / "invalid_prices.xlsx"
    workbook.save(file_path)

    try:
        load_prices_from_excel(file_path)
    except ValueError as exc:
        assert "Excel must contain 'REF'" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing headers")


def test_update_prices_from_map_updates_only_changed_known_skus(capsys):
    variants_api = StubVariantsAPI()
    price_map = {
        "abc-1": 10.99,
        "missing": 5.0,
        "same": 12.5,
    }
    variant_lookup = {
        "ABC-1": {"id": "variant-1", "price": 1000},
        "SAME": {"id": "variant-2", "price": 1250},
    }

    update_prices_from_map(variants_api, price_map, variant_lookup)

    assert variants_api.updates == [{"variant_id": "variant-1", "price": 1099}]
    output = capsys.readouterr().out
    assert "[SKIP] SKU not found: MISSING" in output
    assert "[SKIP] No change for SAME" in output
    assert "[OK] ABC-1: 1000 -> 1099" in output


def test_update_prices_from_map_reports_update_errors(capsys):
    variants_api = StubVariantsAPI(should_fail=True)
    price_map = {"abc-1": 10.99}
    variant_lookup = {"ABC-1": {"id": "variant-1", "price": 1000}}

    update_prices_from_map(variants_api, price_map, variant_lookup)

    output = capsys.readouterr().out
    assert "[ERROR] ABC-1: update failed" in output
