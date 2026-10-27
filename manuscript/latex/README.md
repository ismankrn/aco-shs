# Scaffold manuskrip paper 2 (PeerJ Computer Science)

## Prinsip

Blok abu-abu **POIN** di PDF = inti satu kalimat per bullet (disalin dari
`docs/manuscript-outline.md`). Penulis menulis kalimatnya sendiri, lalu
menghapus blok POIN tersebut. Placeholder merah = keputusan penulis
(judul, caption, diagram kerangka).

## Build

```
cd manuscript/latex
latexmk -pdf main.tex        # naskah utama
latexmk -pdf supplement.tex  # Supplemental Information (tabel S1-S3)
```

## Tabel (jangan diedit manual)

Semua file `tables/*.tex` dihasilkan dari CSV hasil oleh:

```
python scripts/export_latex_tables.py
```

| File | Isi | Sumber |
|---|---|---|
| t_methods | Taksonomi 13 metode (STATIS, edit langsung) | — |
| t_phases | Desain fase eksperimen (STATIS, edit langsung) | — |
| t_datasets | Statistik 4 dataset + positif train/test | runs_p3 + fakta Yamanishi |
| t_reproduction | Reproduksi konfigurasi tesis per seed | runs_p0 |
| t_ablation | Ablasi 2×2×2 + fungsi fitness | runs_p1_merged |
| t_sensitivity | Sensitivitas ρ/K + SA budget-matched | runs_p2b (+default dari runs_p2) |
| t_ratio | Rasio pool × metode (NR) | runs_p2 |
| t_main_f1 | **Tabel inti** 13 metode × 4 dataset | runs_p3 |
| t_tests | Pemenang per dataset + Wilcoxon | runs_p3 |
| t_sa_vs_aco | SA vs ACO per dataset | runs_p3 |
| t_runtime | Runtime per seed (× baseline) | runs_p3 |
| t_abstention | Verifikasi abstensi ACO di Enzyme | runs_p3 |
| s_gmean / s_bas / s_auprc | Matriks metrik suplemen | runs_p3 |

Figur diambil dari `manuscript/F*.pdf` (hasil `scripts/make_figures.py`)
via `\graphicspath{{../}}`.

## Referensi

`references.bib`: 15 entri dipakai ulang dari manuskrip IJ-AI (DOI sudah
terverifikasi Crossref saat penyusunan paper 1) + 8 entri baru paper 2
(terverifikasi, lihat `docs/manuscript-outline.md`). Entri JMLR/NeurIPS
memang tanpa DOI.

## Pindah ke template resmi PeerJ

Submission awal PeerJ bebas format (yang penting nomor baris — sudah via
`lineno`). Bila ingin memakai template `wlpeerj` (Overleaf: "LaTeX template
for PeerJ"), salin isi bagian per bagian; `\input` tabel, `references.bib`,
dan figur bisa dipakai langsung tanpa perubahan.

## Checklist sebelum submit

- [ ] Pilih judul final (3 kandidat di komentar `\title`)
- [ ] Semua blok POIN sudah diganti kalimat dan dihapus
- [ ] Semua `[CAPTION — poin: ...]` sudah ditulis
- [ ] Diagram kerangka SHS (Figure 1) digambar
- [ ] Afiliasi kedua IK dikonfirmasi/dihapus
- [ ] Author contributions (CRediT) difinalkan
- [ ] Tag/rilis GitHub + (opsional) DOI Zenodo untuk Data Availability
- [x] Tabel suplemen dipisah ke file supplemental (supplement.tex)

## Versi Applied Intelligence (Springer)

`manuscript/apin/` berisi port submission untuk Applied Intelligence
(template sn-jnl, sitasi bernomor sn-basic, satu file .tex tanpa
subfolder sesuai aturan Springer):

- `main.tex` — naskah lengkap, tabel di-inline, figur `Fig1..Fig6.pdf`,
  abstrak 250 kata, 6 keyword, bagian Declarations (Funding, Competing
  interests, Data & code availability, Author contributions).
- `supplement_apin.tex` -> `ESM_1.pdf` — Online Resource 1 (Tabel S1-S3).
- Build: `cd manuscript/apin && latexmk -pdf main.tex`.
- Catatan porting: adjustbox tidak kompatibel dengan tabular sn-jnl
  (diganti `\footnotesize` + `\tabcolsep`); kelas meredefinisi
  `\scriptsize` menjadi 9pt; amsmath harus dimuat manual.

`manuscript/latex/` tetap menjadi sumber kebenaran (master); perubahan
konten dilakukan di sana lalu diport.
