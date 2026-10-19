import pathlib
f = pathlib.Path("docs/two_drone_master_bom.md")
if f.exists():
    t = f.read_text()
    t = t.replace("5.330", "5.280")
    t = t.replace("6.330", "6.280")
    t = t.replace("12.660", "12.560")
    t = t.replace("780", "710")
    f.write_text(t)
