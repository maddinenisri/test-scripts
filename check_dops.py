  import os, re, sys
  from urllib.parse import unquote

  if len(sys.argv) != 3:
      print("Usage: python check_dops.py <project_folder> <deployment.dep>")
      sys.exit(1)

  proj, dep_name = sys.argv[1], sys.argv[2]
  dep_dir  = os.path.join(proj, "deployment")
  dep_xml  = open(os.path.join(dep_dir, dep_name), encoding="utf-8").read()
  dop_rels = sorted(set(unquote(m.split("#")[0]) for m in re.findall(r'href="([^"]+\.dop[^"]*)"', dep_xml)))
  print(f"Deployment '{dep_name}' references .dop files: {', '.join(dop_rels)}\n")

  for rel_dop in dop_rels:
      dop = os.path.normpath(os.path.join(dep_dir, rel_dop))
      print(f"==== {rel_dop} ====")
      if not os.path.isfile(dop):
          print("   MISSING .dop FILE <<< PROBLEM\n"); continue
      base = os.path.dirname(dop)
      for tag, href in re.findall(r'<(\w+)[^>]*?href="([^"]+)"', open(dop, encoding="utf-8").read()):
          rel  = unquote(href.split("#")[0])
          full = os.path.normpath(os.path.join(base, rel)) if rel else base
          if tag == "targetRuleProject":
              ok = os.path.isfile(os.path.join(full, ".ruleproject"))
              print(f"   {tag} -> {rel}  = {'OK project folder' if ok else '<<< no .ruleproject (PROBLEM)'}")
          else:                                   # ruleflow / query / variableSet -> must be a FILE
              if not rel:                print(f"   {tag} -> '' EMPTY PATH <<< PROBLEM")
              elif os.path.isfile(full): print(f"   {tag} -> {rel}  = OK file")
              elif os.path.isdir(full):  print(f"   {tag} -> {rel}  <<< FOLDER (PROBLEM)")
              else:                      print(f"   {tag} -> {rel}  <<< MISSING (PROBLEM)")
      print()
