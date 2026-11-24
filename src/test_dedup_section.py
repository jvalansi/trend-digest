from aggregate import dedup_section

if __name__ == "__main__":
    titles = ["SPTI (State Street SPDR Portfolio Intermediate Term Treasury ETF) - 9.0x normal volume",
              "JNK (State Street SPDR Bloomberg High Yield Bond ETF) - 3.4x normal volume"]
    assert len(dedup_section([{"title": t, "source": "ETF Volume"} for t in titles])) == 2
    assert len(dedup_section([{"title": t, "source": "CNBC"} for t in titles])) == 1  # others still merge
    print("ok")
