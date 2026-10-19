import pathlib
for doc in ["docs/judge_demo_summary.md", "docs/judge_demo_checklist.md"]:
    f = pathlib.Path(doc)
    if f.exists():
        t = f.read_text()
        t = t.replace("5.330", "5.280")
        t = t.replace("6.330", "6.280")
        t = t.replace("12.660", "12.560")
        t = t.replace("780", "710")
        f.write_text(t)
