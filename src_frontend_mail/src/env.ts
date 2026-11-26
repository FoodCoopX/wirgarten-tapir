const env: { [key: string]: string } = {};

if (window) {
  if (!window._env_) {
    console.log("Missing _env_ variable on window, using defaults");
    window._env_ = {};
  }

  if (window.parent) {
    const parentKeys = Object.keys(window.parent._env_);
    const prefix = "TAPIRMAIL_";
    parentKeys.forEach((parentKey) => {
      if (!parentKey.startsWith(prefix)) return;
      const localKey = parentKey.replace(prefix, "");
      env[localKey] = window.parent._env_[parentKey];
    });
  }

  const localKeys = Object.keys(window._env_);
  localKeys.forEach((key) => {
    env[key] = window._env_[key];
  });

  const finalKeys = Object.keys(env);
  if (!finalKeys.includes("REACT_APP_API_ROOT")) {
    console.log("REACT_APP_API_ROOT not set, using localhost as default value");
    env["REACT_APP_API_ROOT"] = "http://localhost:8000";
  }

  if (!finalKeys.includes("REACT_APP_BASENAME")) {
    console.log("REACT_APP_BASENAME not set, using / as default value");
    env["REACT_APP_BASENAME"] = "/";
  }
}

export default env;
