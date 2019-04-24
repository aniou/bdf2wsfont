# bdf2wsfont
ad hoc .bdf to wscons .h files font converter

Sample usage:
```
# add licence
cat ~/src/terminus-font-4.47/OFL.TXT | \
   awk 'BEGIN{print "/*"}{ sub("\r$", ""); print " * " $0}END{print " */\n"}' > font_file.h

# convert font to *.h file
   ./bdf_to_wsfont.py -t tables/cp437.txt -i ~/src/terminus-font-4.47/sample_font.bdf >> out/font_file.h
```
