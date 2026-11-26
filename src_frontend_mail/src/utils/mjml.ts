import { IPage, JsonToMjml } from "easy-email-core";
import { MjmlToJson } from "easy-email-extensions";
import mjml2html from "mjml-browser";
import { BODY_BLOCK_TYPE, LAYOUT_BODY_CSS_CLASS } from "../constants/layout";

export { LAYOUT_BODY_CSS_CLASS } from "../constants/layout";

export const markLayoutBodyBlocks = (node: any): any => {
  if (!node || typeof node !== "object") return node;

  const cssClass = node.attributes?.["css-class"];
  const isBodySection =
    typeof cssClass === "string" &&
    cssClass.split(/\s+/).includes(LAYOUT_BODY_CSS_CLASS);

  if (isBodySection) {
    return {
      ...node,
      type: BODY_BLOCK_TYPE,
      title: "E-Mail-Inhalt",
      children: [],
    };
  }

  return {
    ...node,
    children: Array.isArray(node.children)
      ? node.children.map(markLayoutBodyBlocks)
      : node.children,
  };
};

export const containsLayoutBodySection = (node: any): boolean => {
  if (!node || typeof node !== "object") return false;

  const cssClass = node.attributes?.["css-class"];
  if (
    typeof cssClass === "string" &&
    cssClass.split(/\s+/).includes(LAYOUT_BODY_CSS_CLASS)
  ) {
    return true;
  }

  return (
    Array.isArray(node.children) &&
    node.children.some(containsLayoutBodySection)
  );
};

export const mjmlToHtml = (mjmlString: string) => {
  const [fonts, mjml] = extractFonts(mjmlString);

  return mjml2html(mjml, {
    validationLevel: "skip",
    fonts: fonts,
    beautify: false,
  }).html;
};

export const mjmlToJson = (mjmlString: string) => {
  return MjmlToJson(mjmlString);
};

export const jsonToHtml = (content: IPage) => {
  return mjmlToHtml(jsonToMjml(content));
};

export const jsonToMjml = (content: IPage) => {
  return JsonToMjml({
    data: content,
    mode: "production",
    context: content,
    beautify: false,
  })
    .replaceAll("\n", " ")
    .replaceAll("<br>", "<br/>");
};

function decodeHtmlEntities(text: string) {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = text;
  return textarea.value;
}

const extractFonts = (mjml: string) => {
  const safeMjml = decodeHtmlEntities(mjml);
  const parser = new DOMParser();
  const serializer = new XMLSerializer();
  const xmlDoc = parser.parseFromString(safeMjml, "text/xml");
  const mjFontElements = xmlDoc.getElementsByTagName("mj-font");
  let fonts = [];

  for (let i = 0; i < mjFontElements.length; i++) {
    const href = mjFontElements[i].getAttribute("href");
    if (href) {
      fonts.push(href);
    }
  }

  Array.from(mjFontElements).forEach((element) => {
    element.parentNode?.removeChild(element);
  });

  const updatedMjml = serializer.serializeToString(xmlDoc);

  return [fonts, updatedMjml];
};
