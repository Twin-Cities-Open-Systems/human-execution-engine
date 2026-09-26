# hee-print fixture

A small markdown document the `# ci` example renders. It exists so the
man-page example is a real render over a checked-in file, not a live one.

- renders with glow when present
- degrades to bat/batcat, then cat, with a WARNING on stderr
- still exits 0, because the file was rendered
