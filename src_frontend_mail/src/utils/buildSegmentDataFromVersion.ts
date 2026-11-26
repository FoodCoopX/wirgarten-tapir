import { EmailConfigurationVersion, SegmentData } from "tapir-api-client";

export function buildSegmentDataFromVersion(
  version: EmailConfigurationVersion,
): SegmentData {
  return {
    dynamicSegmentNamesAdditive: version.dynamicSegmentsAdditive ?? [],
    dynamicSegmentNamesSubtractive: version.dynamicSegmentsSubtractive ?? [],
    staticSegmentIdsAdditive: version.staticSegmentsAdditive ?? [],
    staticSegmentIdsSubtractive: version.staticSegmentsSubtractive,
    mailCategoryIdsAdditive: version.mailCategoriesAdditive,
  };
}
