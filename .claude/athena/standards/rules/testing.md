---
globs: ["**/tests/**", "**/*test*", "**/*spec*", "conftest.py"]
---
# Testing conventions
- pytest with async support via pytest-asyncio
- Test file mirrors source: `app/api/stocks.py` → `tests/api/test_stocks.py`
- Naming: `test_<function>_<scenario>_<expected>` e.g. `test_get_stock_missing_symbol_returns_404`
- Use factories (factory_boy) for test data. Never hardcode IDs or values
- Database tests: transaction rollback fixture. Never persist test data
- API tests: httpx AsyncClient with app fixture. Test request AND response schemas
- Every bug fix MUST have a regression test that fails without the fix
- Coverage target: 80% minimum on new code
- Mock external services. Never call real APIs in tests
- Financial tests: Decimal with exact comparisons. Never approximate
