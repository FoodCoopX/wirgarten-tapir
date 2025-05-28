const init = (c_p_map_json, pe_c_map_json) => {
  activateGrowingPeriodList(pe_c_map_json);
  activateCapacityList(c_p_map_json);
  activateProductList();
  manageButtons();
  activateDetails();
};

const activateGrowingPeriodList = (pe_c_map_json) => {
  const params = Tapir.getUrlParams();
  const children = Array.from(
    document.getElementById("list_growing_periods").children,
  );
  children.forEach((child) => {
    const id = `period-${params.periodId}`;
    if (child.id === id) {
      child.classList.add("active");
    } else {
      child.classList.remove("active");
    }
  });

  setupCapacityList(params.periodId, pe_c_map_json);
};

const activateCapacityList = (c_p_map_json) => {
  const params = Tapir.getUrlParams();
  const children = Array.from(
    document.getElementById("list_capacities").children,
  );
  const id = `c-${params.capacityId}`;
  children.forEach((child) => {
    if (child.id === id) {
      child.classList.add("active");
    } else {
      child.classList.remove("active");
    }
  });

  setupProductList(params.capacityId, c_p_map_json);
};

const activateProductList = () => {
  const params = Tapir.getUrlParams();
  const items = document.getElementById("list_product").children;
  const children = Array.from(items);
  const id = `p-${params.prodId}`;
  children.forEach((child) => {
    if (child.id === id) {
      child.classList.add("active");
    } else {
      child.classList.remove("active");
    }
  });
};

const setupCapacityList = (periodId, pe_c_map_json) => {
  const pe_c_map = JSON.parse(pe_c_map_json);

  const listItemsTypes = document.getElementById("list_capacities").children;
  const displayIds =
    periodId && pe_c_map[periodId]
      ? pe_c_map[periodId].map((id) => `c-${id}`)
      : [];

  Array.from(listItemsTypes).forEach((item) => {
    item.style["display"] = displayIds.includes(item.id) ? "table-row" : "none";
    item.classList.remove("active");
  });
};

const setupProductList = (capacityId, c_p_map_json) => {
  const c_p_map = JSON.parse(c_p_map_json);

  const listItems = document.getElementById("list_product").children;
  const displayIds =
    capacityId && c_p_map[capacityId]
      ? c_p_map[capacityId].map((id) => `p-${id}`)
      : [];
  Array.from(listItems).forEach((item) => {
    item.style["display"] = displayIds.includes(item.id) ? "table-row" : "none";
    item.classList.remove("active");
  });
};

const manageProductDependentButtons = (params) => {
  if (params.prodId) {
    const buttons = Array.from(document.getElementsByClassName("need-product"));
    buttons.forEach((btn) => {
      btn.removeAttribute("disabled");
    });
  } else {
    const buttons = Array.from(document.getElementsByClassName("need-product"));
    buttons.forEach((btn) => {
      btn.setAttribute("disabled", "true");
    });
  }
};

const manageGrowingPeriodDependentButtons = (params) => {
  const buttons = Array.from(
    document.getElementsByClassName("need-growing-period"),
  );
  buttons.forEach((btn) => {
    const deleteCondition =
      params.periodId &&
      (!btn.classList.contains("delete-btn") ||
        (btn.classList.contains("delete-btn") &&
          allowedActions["period"][params.periodId]["delete"]));
    if (deleteCondition) {
      btn.removeAttribute("disabled");
    } else {
      btn.setAttribute("disabled", "true");
    }
  });
};

const manageCapacityDependentButtons = (params) => {
  const buttons = Array.from(
    document.getElementsByClassName("need-product-type"),
  );
  buttons.forEach((btn) => {
    const deleteCondition =
      params.capacityId &&
      (!btn.classList.contains("delete-btn") ||
        (btn.classList.contains("delete-btn") &&
          (allowedActions["period"][params.periodId]["delete"] ||
            (allowedActions["capacity"][params.capacityId]
              ? allowedActions["capacity"][params.capacityId]["delete"]
              : false))));
    if (deleteCondition) {
      btn.removeAttribute("disabled");
    } else {
      btn.setAttribute("disabled", "true");
    }
  });
};

const manageButtons = () => {
  const params = Tapir.getUrlParams();
  manageGrowingPeriodDependentButtons(params);
  manageCapacityDependentButtons(params);
  manageProductDependentButtons(params);
};

const getCapacityEditForm = () => {
  const params = Tapir.getUrlParams();
  if (params.capacityId) {
    const url = `/tapir/product/${params.periodId}/${
      params.capacityId
    }/typeedit${Tapir.stringifyUrlParams(params)}`;
    FormModal.load(url, "Vertrag / Kapazität editieren");
  }
};

const getCapacityAddForm = () => {
  const params = Tapir.getUrlParams();
  const url = `/tapir/product/${
    params.periodId
  }/typeadd${Tapir.stringifyUrlParams(params)}`;
  FormModal.load(url, "Vertrag / Kapazität hinzufügen");
};

const getProductEditForm = () => {
  const params = Tapir.getUrlParams();
  if (params.prodId) {
    const url = `/tapir/product/${params.periodId}/${params.capacityId}/${
      params.prodId
    }/edit${Tapir.stringifyUrlParams(params)}`;
    FormModal.load(url, "Produkt editieren");
  }
};

const getProductAddForm = () => {
  const params = Tapir.getUrlParams();
  const url = `/tapir/product/${params.periodId}/${
    params.capacityId
  }/add${Tapir.stringifyUrlParams(params)}`;
  FormModal.load(url, "Neues Produkt hinzufügen");
};

const getGrowingPeriodAddForm = () => {
  const params = Tapir.getUrlParams();
  const url = `/tapir/product/periodadd${Tapir.stringifyUrlParams(params)}`;
  const title = "Neue Vertragsperiode anlegen";
  FormModal.load(
    url,
    title,
    "Es wird empfohlen stattdessen die Copy Funktion auf die letzte Periode anzuwenden, damit Produkte und weitere Einstellungen übernommen werden. Diese sind nachträglich noch editierbar.",
    "warning",
  );
};

const getGrowingPeriodCopyForm = () => {
  const params = Tapir.getUrlParams();
  const url = `/tapir/product/${
    params.periodId
  }/periodcopy${Tapir.stringifyUrlParams(params)}`;
  FormModal.load(
    url,
    "Neue Vertragsperiode anlegen",
    "Produkte werden von der gewählten Vertragsperiode übernommen.",
  );
};

// actions
const select_period = (periodId, pe_c_map_json) => {
  const params = Tapir.getUrlParams();
  if (params.periodId !== periodId) {
    params.capacityId = null;
    params.prodId = null;
  }
  params.periodId = periodId;
  Tapir.replaceUrlParams(params);
  activateGrowingPeriodList(pe_c_map_json);
  setupProductList(null, "{}");
  manageButtons();
};

const select_capacity = (capacityId, productTypeId, pt_p_map_json) => {
  const params = Tapir.getUrlParams();
  if (params.capacityId !== capacityId) {
    params.prodId = null;
  }
  params.capacityId = capacityId;
  Tapir.replaceUrlParams(params);

  activateCapacityList(pt_p_map_json);
  manageButtons();
};

const select_product = (productId) => {
  const params = Tapir.getUrlParams();
  params.prodId = productId;
  Tapir.replaceUrlParams(params);
  activateProductList();
  manageButtons();
};

const deleteProduct = () => {
  ConfirmationModal.open(
    "Bist du dir sicher?",
    "Möchtest du dieses Produkt wirklich löschen?",
    "Löschen",
    "danger",
    () => {
      const params = Tapir.getUrlParams();
      const url = `product/${params.periodId}/${params.capacityId}/${
        params.prodId
      }/delete${Tapir.stringifyUrlParams({ ...params, prodId: undefined })}`;
      window.location.replace(url);
    },
  );
};

const deleteCapacity = () => {
  ConfirmationModal.open(
    "Bist du dir sicher?",
    "Möchtest du den Produkttypen wirklich für diese Vertragsperiode löschen?",
    "Löschen",
    "danger",
    () => {
      const params = Tapir.getUrlParams();
      const url = `product/${params.periodId}/${
        params.capacityId
      }/typedelete${Tapir.stringifyUrlParams({
        ...params,
        capacityId: undefined,
      })}`;
      window.location.replace(url);
    },
  );
};

const deleteGrowingPeriod = () => {
  ConfirmationModal.open(
    "Bist du dir sicher?",
    "Möchtest du diese Vertragsperiode wirklich löschen?",
    "Löschen",
    "danger",
    () => {
      const params = Tapir.getUrlParams();
      const url = `product/${
        params.periodId
      }/perioddelete${Tapir.stringifyUrlParams({
        ...params,
        periodId: undefined,
      })}`;
      window.location.replace(url);
    },
  );
};
