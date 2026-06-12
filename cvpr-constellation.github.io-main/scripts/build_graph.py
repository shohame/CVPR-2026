#!/usr/bin/env python3
"""Build graph.json + papers.json for the CVPR Research Constellation.

Pipeline:
  1. Download the CVF Open Access "all papers" listing for a conference, e.g.
       https://openaccess.thecvf.com/CVPR2026?day=all   ->  cvpr_oa.html
  2. Run:
       python scripts/build_graph.py cvpr_oa.html --venue "CVPR 2026"
     Writes graph.json (keyword co-occurrence network) and papers.json
     (one compact record per paper: [title, cvf_stub, [keyword_idx], community, authors]).

Requires: networkx >= 3.0  (pip install networkx)
"""
import argparse, html, json, re, sys
from collections import Counter, defaultdict

import networkx as nx

# canonical keyword -> alias regex (matched against the lowercased title)
KEYWORDS = {
 "Gaussian Splatting": r"gaussian splatting|\bgaussian splat|\b3dgs\b",
 "NeRF": r"\bnerf\b|neural radiance field",
 "Diffusion": r"diffusion",
 "Flow Matching": r"flow matching|rectified flow",
 "3D": r"\b3d\b",
 "Point Cloud": r"point[ -]?clouds?",
 "Segmentation": r"segmentation|segment\b",
 "Detection": r"detection|detector",
 "Vision-Language": r"vision[- ]language|\bvlms?\b",
 "Multimodal": r"multi[- ]?modal",
 "LLM": r"\bllms?\b|large language model",
 "Video": r"\bvideos?\b",
 "Action Recognition": r"action recognition|activity recognition",
 "Pose Estimation": r"pose estimation|\bpose\b",
 "Depth": r"depth",
 "Optical Flow": r"optical flow",
 "Tracking": r"tracking|tracker",
 "Transformer": r"transformer",
 "Attention": r"attention",
 "Self-Supervised": r"self[- ]supervised",
 "Contrastive": r"contrastive",
 "Foundation Model": r"foundation model",
 "CLIP": r"\bclip\b",
 "Text-to-Image": r"text[- ]to[- ]image|\bt2i\b",
 "Text-to-3D": r"text[- ]to[- ]3d",
 "Text-to-Video": r"text[- ]to[- ]video|\bt2v\b",
 "Generation": r"generation|generative|synthesi[sz]",
 "Editing": r"editing",
 "Super-Resolution": r"super[- ]resolution",
 "Restoration": r"restoration|denois|deblur|derain|low[- ]light",
 "Anomaly": r"anomal",
 "Domain Adaptation": r"domain adaptation",
 "Generalization": r"generaliz",
 "Few-Shot": r"few[- ]shot",
 "Zero-Shot": r"zero[- ]shot",
 "Open-Vocabulary": r"open[- ]vocabulary|open[- ]set|open[- ]world",
 "Continual Learning": r"continual|incremental learning|lifelong",
 "Federated": r"federated",
 "Adversarial": r"adversarial",
 "Robustness": r"robust",
 "Distillation": r"distill",
 "Efficient": r"efficient|efficiency|lightweight",
 "Quantization": r"quantiz",
 "Sparse": r"sparse|sparsity|pruning",
 "Rendering": r"render",
 "SLAM": r"\bslam\b",
 "Autonomous Driving": r"autonomous driving|self[- ]driving|\bdriving\b",
 "Medical": r"medical|clinical|pathology|histopath|\bmri\b|\bct\b|radiolog",
 "Face": r"\bfac(e|ial)\b|facial",
 "Re-ID": r"re[- ]identification|\bre[- ]?id\b|person re",
 "Captioning": r"caption",
 "VQA": r"question answering|\bvqa\b",
 "Scene Graph": r"scene graph",
 "Scene Understanding": r"scene understanding",
 "Event Camera": r"event[- ]based|event camera|spiking",
 "Avatar": r"avatar",
 "Human": r"\bhumans?\b",
 "Hand": r"\bhands?\b",
 "Motion": r"motion",
 "Trajectory": r"trajector",
 "Style Transfer": r"style transfer|stylization",
 "Inpainting": r"inpainting|outpainting",
 "Matting": r"matting",
 "Stereo": r"stereo",
 "Multi-View": r"multi[- ]?view",
 "6D Pose": r"6d ?pose|6[- ]?dof",
 "Camera": r"camera",
 "Dataset": r"dataset",
 "Benchmark": r"benchmark",
 "Reinforcement Learning": r"reinforcement",
 "Graph Neural Network": r"graph neural|\bgnn\b",
 "Mamba/SSM": r"\bmamba\b|state[- ]space",
 "Embodied": r"embodied",
 "Navigation": r"navigation|\bvln\b",
 "Grounding": r"grounding|referring",
 "World Model": r"world model",
 "Prompt": r"\bprompt",
 "In-Context": r"in[- ]context",
 "Panoptic": r"panoptic",
 "Implicit/Neural Field": r"neural field|implicit",
 "Autoregressive": r"autoregressive",
 "GAN": r"\bgan\b|generative adversarial",
 "Mesh": r"\bmesh\b",
 "Texture": r"texture",
 "Material/Lighting": r"material|brdf|relighting|\blighting\b|illumination",
 "Geometry": r"geometr",
 "Registration": r"registration",
 "Matching": r"matching|correspondence",
 "Keypoint": r"keypoint|landmark",
 "Document/OCR": r"document|\bocr\b|text spotting|text recognition",
 "Remote Sensing": r"remote sensing|satellite|aerial",
 "Saliency": r"salien",
 "Counting": r"counting",
 "Retrieval": r"retrieval",
 "Compression": r"compression|codec",
 "Forgery/Deepfake": r"deepfake|forgery|watermark",
 "Uncertainty": r"uncertainty",
 "Test-Time": r"test[- ]time",
 "Unsupervised": r"unsupervised",
 "Weakly-Supervised": r"weakly",
 "Semi-Supervised": r"semi[- ]supervised",
 "Classification": r"classification",
 "Optimization": r"optimization",
 "Neural Rendering": r"neural render",
 "Agent": r"\bagents?\b",
 "Reasoning": r"reasoning",
 "Segmentation Anything": r"\bsam\b|segment anything",
 "Image Generation": r"image generation",
 "Object-Centric": r"object[- ]centric",
}

MIN_NODE = 14      # keyword must tag at least this many papers
MAX_NODES = 95     # keep the most frequent keywords
MIN_EDGE = 5       # co-occurrence weight threshold
N_COMMUNITIES = 6  # merge Louvain output into this many groups
LOUVAIN_RES = 1.2
SEED = 7


def parse_listing(path):
    """Yield (title, cvf_stub, authors) per paper from a CVF Open Access listing."""
    doc = open(path, encoding="utf-8", errors="ignore").read()
    papers = []
    for block in re.split(r'<dt class="ptitle">', doc)[1:]:
        m = re.search(r'href="/content/[^/]+/html/(.*?)_paper\.html"[^>]*>(.*?)</a>', block, re.S)
        if not m:
            continue
        stub = re.sub(r"_(CVPR|ICCV|WACV)_\d{4}$", "", m.group(1))
        title = html.unescape(re.sub(r"\s+", " ", m.group(2)).strip())
        authors = ", ".join(re.findall(r'name="query_author" value="(.*?)"', block))
        papers.append((title, stub, authors))
    return papers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("listing", help="saved CVF Open Access ?day=all HTML page")
    ap.add_argument("--venue", default="CVPR 2026")
    args = ap.parse_args()

    papers = parse_listing(args.listing)
    if not papers:
        sys.exit("no papers parsed — is this a CVF Open Access listing page?")
    print(f"parsed {len(papers)} papers")

    pat = {k: re.compile(v) for k, v in KEYWORDS.items()}
    node_count, cooc, paper_kws = Counter(), Counter(), []
    for title, _, _ in papers:
        low = title.lower()
        present = sorted(k for k, p in pat.items() if p.search(low))
        paper_kws.append(present)
        node_count.update(present)
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                cooc[(present[i], present[j])] += 1

    nodes = sorted((k for k, c in node_count.items() if c >= MIN_NODE),
                   key=lambda k: -node_count[k])[:MAX_NODES]
    nset = set(nodes)
    edges = [(a, b, w) for (a, b), w in cooc.items()
             if a in nset and b in nset and w >= MIN_EDGE]
    # drop isolated nodes
    connected = {x for a, b, _ in edges for x in (a, b)}
    nodes = [n for n in nodes if n in connected]
    nset = set(nodes)
    print(f"{len(nodes)} keywords, {len(edges)} links")

    # Louvain communities, then merge small ones into the strongest-linked big one
    G = nx.Graph()
    for a, b, w in edges:
        G.add_edge(a, b, weight=w)
    comms = nx.community.louvain_communities(G, weight="weight",
                                             resolution=LOUVAIN_RES, seed=SEED)
    comms = sorted(comms, key=len, reverse=True)
    big, small = comms[:N_COMMUNITIES], comms[N_COMMUNITIES:]
    comm = {n: i for i, c in enumerate(big) for n in c}
    for c in small:
        for n in c:
            best, bw = 0, -1
            for nb in G[n]:
                if nb in comm and G[n][nb]["weight"] > bw:
                    best, bw = comm[nb], G[n][nb]["weight"]
            comm[n] = best
    print("community sizes:", Counter(comm.values()).most_common())

    idx = {k: i for i, k in enumerate(nodes)}
    graph = {
        "meta": {"papers": len(papers), "keywords": len(nodes),
                 "links": len(edges), "venue": args.venue,
                 "communities": N_COMMUNITIES},
        "nodes": [{"id": k, "count": node_count[k], "community": comm[k]} for k in nodes],
        "links": [{"source": a, "target": b, "weight": w} for a, b, w in edges],
    }
    json.dump(graph, open("graph.json", "w"))

    def paper_comm(kws):
        votes = Counter(comm[k] for k in kws if k in comm)
        return votes.most_common(1)[0][0] if votes else -1

    out = [[t, s, [idx[k] for k in kws if k in idx], paper_comm(kws), au]
           for (t, s, au), kws in zip(papers, paper_kws)]
    json.dump(out, open("papers.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print("wrote graph.json + papers.json")
    print("NOTE: if the keyword set changed, update COMM names / TOPIC_OF in index.html")


if __name__ == "__main__":
    main()
