import env from "../env";

export function getMediaLibraryFileUrl(uploadId: string): string {
  return (
    (env.REACT_APP_API_ROOT as string) +
    "/api/media_library/get_file/" +
    uploadId
  );
}
