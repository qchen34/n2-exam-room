// pdfkit-tool.swift — PDF ページの画像化／日本語 OCR（macOS 標準フレームワークのみ）
// 使い方:
//   swiftc -O -o /tmp/pdfkit-tool pdfkit-tool.swift
//   /tmp/pdfkit-tool img  <pdf> <outdir> <scale> [from] [to]
//   /tmp/pdfkit-tool ocr  <pdf> [from] [to]
import Foundation
import PDFKit
import AppKit
import Vision

func parse(_ args: [String], _ i: Int) -> Int? { i < args.count ? Int(args[i]) : nil }

func renderPage(_ page: PDFPage, scale: CGFloat) -> CGImage? {
    let box = page.bounds(for: .mediaBox)
    let w = Int(box.width * scale), h = Int(box.height * scale)
    guard w > 0, h > 0 else { return nil }
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: CGFloat(w), height: CGFloat(h)))
    ctx.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: ctx)
    return ctx.makeImage()
}

func ocr(_ img: CGImage, lang: [String]) -> String {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    req.recognitionLanguages = lang
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    do { try handler.perform([req]) } catch { return "" }
    guard let obs = req.results else { return "" }
    // 上から下へ、行ごとにまとめる
    let lines = obs.compactMap { o -> (CGFloat, CGFloat, String)? in
        guard let c = o.topCandidates(1).first else { return nil }
        let bb = o.boundingBox
        return (1 - bb.midY, bb.minX, c.string)
    }.sorted { a, b in a.0 == b.0 ? a.1 < b.1 : a.0 < b.0 }
    return lines.map { $0.2 }.joined(separator: "\n")
}

let args = CommandLine.arguments
guard args.count >= 2 else { print("usage: img|ocr ..."); exit(2) }
let mode = args[1]
guard args.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: args[2])) else {
    print("PDF を開けない"); exit(2)
}
let total = doc.pageCount
let from = parse(args, mode == "img" ? 5 : 3) ?? 1
let to = parse(args, mode == "img" ? 6 : 4) ?? total

if mode == "img" {
    guard args.count >= 4 else { print("outdir が必要"); exit(2) }
    let outdir = args[3]
    try? FileManager.default.createDirectory(atPath: outdir, withIntermediateDirectories: true)
    let scale = CGFloat(Double(args.count > 4 ? args[4] : "2.0") ?? 2.0)
    for i in max(1, from)...min(total, to) {
        guard let page = doc.page(at: i - 1), let cg = renderPage(page, scale: scale) else { continue }
        let rep = NSBitmapImageRep(cgImage: cg)
        guard let data = rep.representation(using: .png, properties: [:]) else { continue }
        let path = "\(outdir)/p\(String(format: "%02d", i)).png"
        try? data.write(to: URL(fileURLWithPath: path))
        print(path)
    }
} else {
    for i in max(1, from)...min(total, to) {
        guard let page = doc.page(at: i - 1), let cg = renderPage(page, scale: 2.2) else { continue }
        let text = ocr(cg, lang: ["ja-JP", "en-US"])
        print("=== page \(i) ===")
        print(text)
    }
}
