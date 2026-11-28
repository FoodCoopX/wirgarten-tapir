import { lazy } from "react";

const Dashboard = lazy(() => import("./pages/dashboard"));
const EmailConfigurationEditor = lazy(
  () => import("./pages/email-configuration/editor"),
);
const MediaLibrary = lazy(() => import("./pages/media_library"));
const TemplateEditor = lazy(() => import("./pages/template-editor"));

const Paths = {
  dashboard: "/",
  emailConfigurationCreate: "/emailconfiguration/new",
  emailConfigurationEdit: "/emailconfiguration/edit/:id",
  templateEditorCreate: "/editor",
  templateEditorEdit: "/editor/:templateId",
  mediaLibrary: "/media_library",
};

const routes = [
  {
    path: Paths.dashboard,
    element: Dashboard,
  },
  {
    path: Paths.emailConfigurationCreate,
    element: EmailConfigurationEditor,
  },
  {
    path: Paths.emailConfigurationEdit,
    element: EmailConfigurationEditor,
  },
  {
    path: Paths.templateEditorCreate,
    element: TemplateEditor,
  },
  {
    path: Paths.templateEditorEdit,
    element: TemplateEditor,
  },
  {
    path: Paths.mediaLibrary,
    element: MediaLibrary,
  },
];

export default Paths;
export { routes };
