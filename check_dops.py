  import os, re, sys

  if len(sys.argv) != 3:
      print("Usage: python check_dops.py <project_folder> <deployment.dep>")
      print(r'Example: python check_dops.py "C:\workspace\rule_evaluator\panorama-application" "localhost_9_0930_app_ui.dep"')
      sys.exit(1)

  proj = sys.argv[1]
  dep_name = sys.argv[2]
  
  dep_dir = os.path.join(proj, "deployment")
  dep_path = os.path.join(dep_dir, dep_name)

  dep_xml = open(dep_path, encoding="utf-8").read()

  # the real .dop files are in the <operation href="....dop#uuid"/> entries
  dop_rels = sorted(set(m.split("#")[0] for m in re.findall(r'href="([^"]+\.dop[^"]*)"', dep_xml)))
  print(f"Deployment '{dep_name}' references .dop files: {', '.join(dop_rels)}\n")

  for rel_dop in dop_rels:
      dop = os.path.normpath(os.path.join(dep_dir, rel_dop))
      print(f"==== {rel_dop} ====")
      if not os.path.isfile(dop):
          print("   MISSING .dop FILE <<< PROBLEM\n")
          continue
      base = os.path.dirname(dop)          # resolve this .dop's hrefs relative to ITS folder
      x = open(dop, encoding="utf-8").read()
      for tag, href in re.findall(r'<(\w+)[^>]*?href="([^"]+)"', x):
          rel = href.split("#")[0]
          if not rel:
              print(f"   {tag} -> '' EMPTY PATH (=folder) <<< PROBLEM")
              continue
          full = os.path.normpath(os.path.join(base, rel))
          if os.path.isfile(full):
              print(f"   {tag} -> {rel}  = OK file")
          elif os.path.isdir(full):
              print(f"   {tag} -> {rel}  <<< FOLDER (PROBLEM)")
          else:
              print(f"   {tag} -> {rel}  <<< MISSING (PROBLEM)")
      print()
  
