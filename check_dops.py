  import os, re, sys
  from urllib.parse import unquote

  if len(sys.argv) != 2:
      print("Usage: python check_paths.py <project_folder>")
      sys.exit(1)

  proj = os.path.abspath(sys.argv[1])
  workspace = os.path.dirname(proj)          # platform:/ resolves against the project's PARENT
  xml = open(os.path.join(proj, ".ruleproject"), encoding="utf-8").read()
  print(f"project   = {proj}\nworkspace = {workspace}\n")

  def resolve(val):
      for scheme in ("platform:/", "xom:/"):
          if val.startswith(scheme):
              full = os.path.normpath(os.path.join(workspace, unquote(val[len(scheme):])))
              if   os.path.isfile(full): return f"{full}  = OK file"
              elif os.path.isdir(full):  return f"{full}  <<< FOLDER (PROBLEM)"
              else:                      return f"{full}  <<< MISSING (PROBLEM)"
      return f"{val}  (non-platform, ignored)"

  for tag in re.findall(r'<entries\b[^>]*?/?>', xml):
      a = lambda k: (re.search(k + r'="([^"]*)"', tag) or [None, None])[1]
      print(f"- name={a('name')}  type={a('xsi:type')}  kind={a('kind')}")
      for k in ("url", "origin"):
          if a(k): print(f"    {k}={a(k)}\n       -> {resolve(a(k))}")
      print()
