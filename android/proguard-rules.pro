# Regole di R8 per l'APK (lette da build_apk.py insieme a bin/aapt_rules.pro).
# Le classi nominate nel manifest e nei layout (activity, servizio, receiver, widget, provider) le tiene già
# aapt2 in bin/aapt_rules.pro: tutto il resto viene rinominato con nomi corti e illeggibili (a, b, c...).
# L'app non usa riflessione né @JavascriptInterface: se un giorno servisse, la classe va tenuta qui con -keep.

# Numeri di riga negli errori: con bin/mapping/ si ritrovano classe e metodo originali (retrace)
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

# Nomi di classi e metodi lasciati leggibili (06/11/2026): Google Play Protect segnalava l'app come "dannosa" e la
# prima versione segnalata (4.12.4, 27/10) era uscita il giorno dopo l'introduzione dei nomi illeggibili. R8 continua
# a togliere il codice non usato e a ottimizzare; il codice e' comunque pubblico (GPL-3.0, QMon31/Voxarium).
-dontobfuscate
