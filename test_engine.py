"""Run: python test_engine.py"""
import datetime as dt
import engine as E

T = dt.date(2026, 11, 9)


def run(L, s):
    return E.handle(L, s, source="test", today=T)


def test_all():
    L = E.new_ledger()
    run(L, "आज शर्मा जी की साइट पे काम किया, सात सौ तय हुआ था, चार सौ मिले")
    a = E.accounts(L)["srm"]
    assert (a["days"], a["rate"], a["paid"], a["due"]) == (1, 700, 400, 300)
    assert a["below_min"] and a["shortfall"] == 140           # 840 - 700

    run(L, "kal bhi Sharma ji ke yahan kaam kiya")            # Roman script, same contractor
    assert E.accounts(L)["srm"]["days"] == 2
    assert L["records"][-1]["entries"][0]["date"] == "2026-11-08"

    run(L, "वर्मा ठेकेदार के यहाँ आधा दिन काम किया, रेट 900 रोज़")
    v = E.accounts(L)["vrm"]
    assert v["days"] == 0.5 and v["earned"] == 450 and not v["below_min"]

    run(L, "आज 2 घंटे ओवरटाइम भी किया")                      # goes to last contractor
    assert E.accounts(L)["vrm"]["ot_pay"] == 900 / 8 * 2 * 2

    run(L, "Gupta seth ke ghar pe 3 din kaam kiya 900 rupaye din ka")
    run(L, "gupta ji se 1500 advance liya")
    assert E.accounts(L)["gpt"]["due"] == 2700 - 1500

    r = run(L, "galti ho gayi hata do")                        # voids the advance
    assert r["intent"] == "undo" and E.accounts(L)["gpt"]["due"] == 2700

    assert run(L, "शर्मा जी पर कितना बाकी है")["intent"] == "query"
    assert run(L, "शर्मा जी का हिसाब सुनाओ")["intent"] == "statement"
    assert run(L, "शर्मा जी ने पैसे नहीं दिए")["intent"] == "note"
    assert run(L, "हेलो")["intent"] == "unknown"

    assert E.verify_chain(L)["ok"]
    L["records"][1]["entries"][0]["days"] = 0.5                # tamper
    assert E.verify_chain(L) == {"ok": False, "broken_at": 2}
    print("all engine tests passed")


if __name__ == "__main__":
    test_all()
