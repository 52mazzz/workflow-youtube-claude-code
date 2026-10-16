"""Serveur de la page d'écoute des musiques (musique.py ecoute), avec les requêtes partielles (Range) : sans elles,
Chrome ne peut pas avancer dans un morceau (le serveur http.server de Python ne les gère pas ; demande du 2026-10-16).
usage : python scripts/serveur_ecoute.py <port> <dossier>"""
import http.server
import os
import re
import sys


class Gestion(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        plage = self.headers.get("Range")
        chemin = self.translate_path(self.path)
        if not plage or os.path.isdir(chemin) or not os.path.exists(chemin):
            return super().send_head()
        taille = os.path.getsize(chemin)
        m = re.match(r"bytes=(\d*)-(\d*)", plage)
        debut = int(m.group(1)) if m and m.group(1) else 0
        fin = int(m.group(2)) if m and m.group(2) else taille - 1
        fin = min(fin, taille - 1)
        if debut > fin:
            self.send_error(416)
            return None
        f = open(chemin, "rb")
        f.seek(debut)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(chemin))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {debut}-{fin}/{taille}")
        self.send_header("Content-Length", str(fin - debut + 1))
        self.end_headers()
        self._reste = fin - debut + 1
        return f

    def copyfile(self, source, outputfile):
        reste = getattr(self, "_reste", None)
        if reste is None:
            return super().copyfile(source, outputfile)
        while reste > 0:
            bloc = source.read(min(65536, reste))
            if not bloc:
                break
            outputfile.write(bloc)
            reste -= len(bloc)

    def end_headers(self):
        if not self.headers.get("Range"):
            self.send_header("Accept-Ranges", "bytes")
        super().end_headers()


if __name__ == "__main__":
    port, dossier = int(sys.argv[1]), sys.argv[2]
    os.chdir(dossier)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Gestion).serve_forever()
