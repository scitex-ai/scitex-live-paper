"""Exercise the public rich provider and native adapter using real PDF.js.

Disposable HTTP port fixtures are controlled here; no live services/projects.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--pdfjs-root", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    js = repo / "src/scitex_live_paper/_django/static/live_paper/js"
    css = repo / "src/scitex_live_paper/_django/static/live_paper/css/pdf-provider.css"
    sdk = args.sdk_root / "src/scitex_sdk/ui/static/scitex_sdk/ui/js/app/pdf-viewer.js"
    vendor = (args.pdfjs_root or args.sdk_root / "node_modules/pdfjs-dist") / "build"
    fixture = repo / "tests/scitex_live_paper/fixtures/rich-provider.pdf"
    html = """<meta name="live-paper-csrf-token" content="native-fixture-token"><main id="root"><div id="viewer" style="width:750px;height:480px;overflow:auto"></div></main>
<script type="module">
import {createPdfViewer} from '/sdk.js';import * as pdfjs from '/pdf.mjs';
import {createRichPdfViewer} from '/modules/pdf-provider.js';
import {PDFViewer} from '/modules/pdf-viewer.js';import * as nativePdfjs from '/native-pdf.mjs';
nativePdfjs.GlobalWorkerOptions.workerSrc='/native-worker.mjs';window.nativePdfjs=nativePdfjs;
window.pdfjs=pdfjs;window.SDKFactory=createPdfViewer;window.NativeViewer=PDFViewer;window.events=[];window.calls=[];
window.overlayFeed=[{id:'editable',page:1,bbox:[60,620,240,655],label:'Editable claim',status:'verified'},{id:'locked',page:1,bbox:[100,400,220,450],label:'Locked provenance',readonly:true}];
window.markCalls=[];
window.commentFeed=[{id:'seed',body:'Existing note',target:{overlayId:'editable'}}];
window.provider=createRichPdfViewer({container:document.querySelector('#viewer'),createPdfViewer,rendererOptions:{pdfjs,workerSrc:'/pdf.worker.mjs',textLayer:true,linkLayer:true},ports:{documents:{resolve:key=>({id:key,src:'/fixture.pdf'})},overlays:{list:()=>overlayFeed},comments:{list:()=>commentFeed,create:async(doc,target,body)=>{calls.push({doc:doc.id,target,body});if(window.refuse)throw new Error('Fixture server refused this mutation');let item={id:'saved-'+calls.length,body,target};commentFeed.push(item);return item;}},mutations:{createMark:(_doc,input)=>{markCalls.push(input);if(window.markRefuse)throw new Error('Mark mutation refused')}},policy:{canMutate:()=>!window.policyDenied},events:{emit:e=>events.push(e)}}});
provider.renderer.setInteractive(false);await provider.load('document-one');window.ready=true;
</script>"""
    writes = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        def serve(route):
            path = (
                route.request.url.split("?", 1)[0].split("://", 1)[1].split("/", 1)[-1]
            )
            if path == "sdk.js":
                route.fulfill(content_type="text/javascript", body=sdk.read_bytes())
            elif path in ["native-pdf.mjs", "native-worker.mjs"]:
                name = (
                    "pdf.min.mjs" if path == "native-pdf.mjs" else "pdf.worker.min.mjs"
                )
                route.fulfill(
                    content_type="text/javascript",
                    body=(js.parent / "pdfjs" / name).read_bytes(),
                )
            elif path in ["pdf.mjs", "pdf.worker.mjs"]:
                route.fulfill(
                    content_type="text/javascript", body=(vendor / path).read_bytes()
                )
            elif path == "fixture.pdf" or path == "native/api/pdf":
                route.fulfill(content_type="application/pdf", body=fixture.read_bytes())
            elif path.startswith("modules/"):
                member = (js / path.removeprefix("modules/")).resolve()
                assert member.is_relative_to(js)
                route.fulfill(content_type="text/javascript", body=member.read_bytes())
            elif path == "native/api/comments":
                assert (
                    route.request.headers.get("x-csrftoken") == "native-fixture-token"
                )
                body = route.request.post_data_json
                writes.append(body)
                route.fulfill(
                    json={"comment": {"id": "native-saved", **body["comment"]}}
                )
            else:
                route.fulfill(content_type="text/html", body=html)

        page.route("http://rich.test/**", serve)
        page.goto("http://rich.test/?working_dir=fixture")
        page.add_style_tag(content=css.read_text())
        page.wait_for_function("window.ready===true")
        assert page.locator("#viewer canvas").count() == 4
        editable = page.get_by_role("button", name="Editable claim", exact=True)
        assert editable.locator(".lp-rich-comment-count").inner_text() == "✎1"
        editable.click()
        assert (
            page.get_by_role("dialog", name="PDF comments")
            .get_by_text("Existing note")
            .is_visible()
        )
        page.get_by_role("textbox", name="New PDF comment").fill("New fixture note")
        page.get_by_role("button", name="Add comment").click()
        page.get_by_text("New fixture note", exact=True).wait_for()
        assert page.evaluate("calls.length") == 1
        page.get_by_role("button", name="Close comments").click()
        page.get_by_role("button", name="Locked provenance").click()
        assert page.get_by_role("textbox", name="New PDF comment").is_disabled()
        refused = page.evaluate(
            """async()=>{try{await provider.createComment({overlayId:'locked'},'Bypass attempt');return false}catch(e){return e.message}}"""
        )
        assert "refused" in refused and page.evaluate("calls.length") == 1
        page.get_by_role("button", name="Close comments").click()
        editable.click()
        page.evaluate("window.refuse=true")
        page.get_by_role("textbox", name="New PDF comment").fill("Rejected text")
        page.get_by_role("button", name="Add comment").click()
        page.get_by_role("status").get_by_text(
            "Fixture server refused this mutation"
        ).wait_for()
        assert (
            page.get_by_role("textbox", name="New PDF comment").input_value()
            == "Rejected text"
        )
        assert page.evaluate("commentFeed.length") == 2
        page.evaluate("window.refuse=false;window.policyDenied=true")
        denied = page.evaluate(
            """async()=>{try{await provider.createComment({overlayId:'editable'},'Policy bypass');return false}catch(e){return e.message}}"""
        )
        assert "refused" in denied and page.evaluate("calls.length") == 2
        page.evaluate("window.policyDenied=false;provider.refresh()")
        page.evaluate('provider.load("document-two")')
        assert page.locator(".lp-rich-comments").count() == 0
        assert (
            page.evaluate(
                'events.filter(e=>e.type==="document-loaded").at(-1).documentId'
            )
            == "document-two"
        )
        # Real Pointer Events reach the mutation port only after policy checks.
        page.evaluate(
            "provider.renderer.setInteractive(true);document.querySelector('#viewer').scrollTop=0;document.querySelector('#viewer').scrollLeft=0"
        )
        box = page.locator("#viewer").bounding_box()

        def draw():
            page.mouse.move(box["x"] + 350, box["y"] + 250)
            page.mouse.down()
            page.mouse.move(box["x"] + 400, box["y"] + 290, steps=4)
            page.mouse.up()

        draw()
        page.wait_for_function("markCalls.length===1")
        page.evaluate("window.policyDenied=true")
        draw()
        assert page.evaluate("markCalls.length") == 1
        page.evaluate("window.policyDenied=false;window.markRefuse=true")
        draw()
        page.wait_for_function(
            'events.some(e=>e.type==="mutation-error" && e.action==="mark-create")'
        )
        assert page.evaluate("markCalls.length") == 2
        # Native consumer adapter, same actual SDK and public provider.
        page.evaluate(
            """async()=>{provider.destroy();window.nativeEvents=[];document.querySelector('#root').addEventListener('live-paper:claim',e=>nativeEvents.push(e.detail));window.native=new NativeViewer({container:document.querySelector('#viewer'),createPdfViewer:SDKFactory,pdfjs:nativePdfjs,workerSrc:'/native-worker.mjs',apiBase:'/native/api/'});native.setClaims([{claim_id:'native-claim',claim_value:'Native claim',status:'verified',extras:{anchor:{page:1,bbox:[60,620,240,655]}}}]);native.setComments([{id:'native-seed',body:'Native note',target:{claim_id:'native-claim'}}]);if(!await native.load())throw new Error('Native adapter load failed');}"""
        )
        assert page.locator(".stx-pdf-text-layer").count() == 2
        page.get_by_role("button", name="Native claim", exact=True).click()
        assert page.evaluate("nativeEvents[0].id") == "native-claim"
        page.get_by_role("textbox", name="New PDF comment").fill("Native adapter note")
        page.get_by_role("button", name="Add comment").click()
        page.get_by_text("Native adapter note", exact=True).wait_for()
        assert writes == [
            {
                "comment": {
                    "body": "Native adapter note",
                    "target": {"claim_id": "native-claim"},
                }
            }
        ], writes
        missing = page.evaluate(
            """async()=>{document.querySelector('meta[name="live-paper-csrf-token"]').remove();try{const {postComment}=await import('/modules/comments.js');await postComment('/native/api/',{body:'Blocked missing token',target:{claim_id:'native-claim'}});return ''}catch(error){return error.message}}"""
        )
        assert "CSRF token missing" in missing
        assert len(writes) == 1
        page.evaluate("native.destroy()")
        assert page.locator("#viewer").evaluate("(el)=>el.childElementCount") == 0
        assert errors == [], errors
        print(
            json.dumps(
                {
                    "pdf_pages": 2,
                    "overlay_and_count": True,
                    "comments": [
                        "create",
                        "canonical lock refusal",
                        "policy refusal",
                        "failed save retained draft",
                        "reload clears popup",
                    ],
                    "native_adapter": [
                        "claim selection event",
                        "DTO translated POST",
                        "text layer retained",
                    ],
                    "native_fixture_posts": len(writes),
                    "page_errors": errors,
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
