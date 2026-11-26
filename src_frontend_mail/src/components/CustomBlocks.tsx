import {
  BasicType,
  BlockManager,
  components,
  createCustomBlock,
  IBlockData,
} from "easy-email-core";
import { BODY_BLOCK_TYPE, LAYOUT_BODY_CSS_CLASS } from "../constants/layout";

type IBodyBlock = IBlockData<{
  padding?: string;
  "background-color"?: string;
}>;

const BodyBlock = (() => {
  const MjmlBlock = components.MjmlBlock as any;
  const Column = components.Column as any;
  const Text = components.Text as any;
  const Raw = components.Raw as any;

  return createCustomBlock<IBodyBlock>({
    name: "E-Mail-Inhalt",
    type: BODY_BLOCK_TYPE,
    validParentType: [BasicType.PAGE, BasicType.WRAPPER],
    create(payload) {
      return {
        type: BODY_BLOCK_TYPE,
        title: "E-Mail-Inhalt",
        data: { value: {} },
        attributes: {
          "css-class": LAYOUT_BODY_CSS_CLASS,
          padding: "0px",
          "background-color": "#ffffff",
          ...payload?.attributes,
        },
        children: [],
      } as IBodyBlock;
    },
    render({ data, idx, mode }) {
      return (
        <MjmlBlock
          idx={idx}
          type={BasicType.SECTION}
          attributes={{
            "css-class": data.attributes["css-class"] ?? LAYOUT_BODY_CSS_CLASS,
            padding: data.attributes.padding ?? "0px",
            "background-color":
              data.attributes["background-color"] ?? "#ffffff",
          }}
        >
          <Column>
            {mode === "testing" ? (
              <Text
                value={{ content: "{{Body}}" }}
                attributes={{ "css-class": "tapir-layout-body-token" }}
              />
            ) : (
              <Raw value={{ content: "{{Body}}" }} />
            )}
          </Column>
        </MjmlBlock>
      );
    },
  });
})();

BlockManager.registerBlocks({ [BODY_BLOCK_TYPE]: BodyBlock });
