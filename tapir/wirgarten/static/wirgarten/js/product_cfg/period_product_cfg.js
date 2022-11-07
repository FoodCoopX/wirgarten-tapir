const init = (pt_p_map_json, pe_pt_map_json) => {
    activateGrowingPeriodList(pe_pt_map_json)
    activateProductTypeList(pt_p_map_json)
    activateProductList();
    manageButtons();
    activateDetails();
}

// Helper
const stringifyUrlParams = (params) => {
   return '?' + Object.entries(params)
                    .filter(p => p[0] && p[1])
                    .map(p => `${p[0]}=${p[1]}` )
                    .join('&')
}

const getUrlParams = () =>
    Object.fromEntries(
        window.location.search.substring(1)
        .split('&')
        .map(kv => kv.split('=')))

const replaceUrlParams = (params) =>
    history.replaceState({}, null, window.location.pathname + stringifyUrlParams(params));

// page logic
const activateDetails = () => {
    const params = getUrlParams();
    const type_list = Array.from(document.getElementsByClassName('list_details_product_types'));
    type_list.forEach(item =>  {
        const sChildren = Array.from(item.children);
        sChildren.forEach(elem => elem.style['display'] = 'none');
    })
    const prod_lists = Array.from(document.getElementsByClassName('list_details_products'));
    prod_lists.forEach(item =>  {
        const sChildren = Array.from(item.children);
        sChildren.forEach(elem => elem.style['display'] = 'none');
    })
    const period_list = Array.from(document.getElementById('list_details_growing_periods').children);
    period_list.forEach(item => item.style['display'] = 'none');

    if (params.periodId) {
        const sActiveElement = "details_growing_period_" + params.periodId;
        const elem = document.getElementById(sActiveElement);
        elem.style.display = "grid";
    }
    if (params.prodTypeId) {
        const sActiveElement = "details_product_type_" + params.prodTypeId + params.periodId;
        const elem = document.getElementById(sActiveElement);
        elem.style.display = "grid";
    }
    if (params.prodId) {
        const sActiveElement = "details_product_" + params.prodId + params.periodId;
        document.getElementById(sActiveElement).style.display = "grid";
    }
}

const activateGrowingPeriodList = (pe_pt_map_json) => {
    const params = getUrlParams();
    const children = Array.from(document.getElementById('list_growing_periods').children);
    children.forEach(child => {
        child.classList.remove("active");
    });

    if(params.periodId) {
        document.getElementById(`btn_period_${params.periodId}`).classList.add("active");

        setupProductTypeList(params.periodId, pe_pt_map_json);
    }
}

const activateProductTypeList = (pt_p_map_json) => {
    const params = getUrlParams();
    const children = Array.from(document.getElementById('list_product_types').children);
    children.forEach(child => {
        child.classList.remove("active");
    });

    if(params.prodTypeId) {
        document.getElementById(`btn_prtype_${params.prodTypeId}`).classList.add("active");
        setupProductList(params.prodTypeId, pt_p_map_json);
    }
}

const activateProductList = () => {
    const params = getUrlParams();
    const items = document.getElementById('list_product').children;
    const children = Array.from(items);
    children.forEach(child => {
        child.classList.remove("active");
    });

    if(params.prodId)
        document.getElementById(`btn_prod_${params.prodId}`).classList.add("active");
}

const setupProductTypeList = (periodId, pe_pt_map_json) => {
    const pe_pt_map = JSON.parse(pe_pt_map_json);

    const listItemsTypes = document.getElementById("list_product_types").children;
    Array.from(listItemsTypes).forEach(item =>  {
        item.style['display'] = 'none';
        item.classList.remove("active");
    })
    const listItemsProds = document.getElementById("list_product").children;
    Array.from(listItemsProds).forEach(item =>  {
        item.style['display'] = 'none';
        item.classList.remove("active");
    })
    if (pe_pt_map[periodId] != undefined) {
        pe_pt_map[periodId].forEach(productTypeId => {
            const sActiveElement = "btn_prtype_" + productTypeId;
            // sort to front to prevent artifacts
            let elem = document.getElementById(sActiveElement);
            let parent = elem.parentElement;
            parent.removeChild(elem);
            parent.prepend(elem);
            elem.style.display = "grid";
        });
    }
}

const setupProductList = (productTypeId, pt_p_map_json) => {
    const pt_p_map = JSON.parse(pt_p_map_json);

    const listItems = document.getElementById("list_product").children;
    Array.from(listItems).forEach(item =>  {
        item.style['display'] = 'none';
        item.classList.remove("active");
    })
    if (pt_p_map[productTypeId] != undefined)
        pt_p_map[productTypeId].forEach(productId => {
            // console.log(" -ptId: ", productTypeId, " -pId: ", productId)
            const sActiveElement = "btn_prod_" + productId;
            let elem = document.getElementById(sActiveElement);
            let parent = elem.parentElement;
            parent.removeChild(elem);
            parent.prepend(elem);
            elem.style.display = "grid";
        });
}

const manageProductDependentButtons = (params) => {
    if (params.prodId) {
        const buttons = Array.from(document.getElementsByClassName("need-product"));
        buttons.forEach(btn => {
            btn.removeAttribute("disabled");
        })
    } else {
        const buttons = Array.from(document.getElementsByClassName("need-product"));
        buttons.forEach(btn => {
            btn.setAttribute("disabled", "true");
        })
    }
}

const manageGrowingPeriodDependentButtons = (params) => {
    const buttons = Array.from(document.getElementsByClassName("need-growing-period"));
    if (params.periodId) {
        buttons.forEach(btn => {
            btn.removeAttribute("disabled");
        })
    } else {
        buttons.forEach(btn => {
            btn.setAttribute("disabled", "true");
        })
    }
}

const manageProductTypeDependentButtons = (params) => {
    const buttons = Array.from(document.getElementsByClassName("need-product-type"));
    if (params.prodTypeId) {
        buttons.forEach(btn => {
            btn.removeAttribute("disabled");
        })
    } else {
        buttons.forEach(btn => {
            btn.setAttribute("disabled", "true");
        })
    }
}

const manageButtons = () => {
    const params = getUrlParams();
    manageGrowingPeriodDependentButtons(params);
    manageProductTypeDependentButtons(params);
    manageProductDependentButtons(params);
}

// dynamic Forms
const AddModal = (url, title) => {
    document.getElementById("modalForm").action = url;
    fetch(url).then(form => {
        form.text().then(html => {
            document.getElementById("productModalContainer").innerHTML = html;
        });
    })
    document.getElementById("modalLabel").innerHTML = title;
}

const getProductTypeEditForm = () => {
    const params = getUrlParams();
    if (params.prodTypeId) {
        const url = `/wirgarten/product/${params.prodTypeId}/${params.periodId}/typeedit${stringifyUrlParams(params)}`;
        AddModal(url, "Produkt Typ editieren");
    }
}

const getProductTypeAddForm = () => {
    const params = getUrlParams();
    const url = `/wirgarten/product/${params.periodId}/typeadd${stringifyUrlParams(params)}`;
    AddModal(url, "Neuen Produkt Typ hinzufügen");
}

const getProductEditForm = () => {
    const params = getUrlParams();
    if (params.prodId) {
        const url = `/wirgarten/product/${params.prodId}/edit${stringifyUrlParams(params)}`;
        AddModal(url, "Produkt editieren");
    }
}

const getProductAddForm = () => {
    const params = getUrlParams();
    const url = `/wirgarten/product/${params.prodTypeId}/add${stringifyUrlParams(params)}`;
    AddModal(url, "Neues Produkt hinzufügen");
}

const getGrowingPeriodAddForm = () => {
    const params = getUrlParams();
    const url = `/wirgarten/product/periodadd${stringifyUrlParams(params)}`;
    const title = `Neue Anbauperiode anlegen. Ohne Produkte
     Es wird empfohlen stattdessen die Copy Funktion auf die letzte Periode Anzuwenden,
     damit Produkte und weitere Einstellungen übernommen werden. Diese sind noch nachträglich editierbar.`;
    AddModal(url, title);
}

const getGrowingPeriodCopyForm = () => {
    const params = getUrlParams();
    const url = `/wirgarten/product/${params.periodId}/periodcopy${stringifyUrlParams(params)}`;
    AddModal(url, "Neue Anbauperiode anlegen. Produkte werden übernommen.");
}

// actions
const select_period = (periodId, pe_pt_map_json) => {
    const params = getUrlParams();
    if(params.periodId !== periodId) {
        params.prodTypeId = null;
        params.prodId = null;
    }
    params.periodId = periodId;
    replaceUrlParams(params);
    activateGrowingPeriodList(pe_pt_map_json);
    activateDetails();
    manageButtons();
}

const select_product_type = (productTypeId, pt_p_map_json) => {
    const params = getUrlParams();
    if(params.prodTypeId !== productTypeId) {
        params.prodId = null;
    }
    params.prodTypeId = productTypeId;
    replaceUrlParams(params);
    activateProductTypeList(pt_p_map_json);
    activateDetails();
    manageButtons();
}

const select_product = (productId) => {
    const params = getUrlParams();
    params.prodId = productId;
    replaceUrlParams(params);
    activateProductList();
    activateDetails();
    manageButtons();
}

const deleteProduct = () => {
    const params = getUrlParams();
    const url = `product/${params.prodId}/delete${stringifyUrlParams({...params, prodId: undefined})}`;
    window.location.replace(url)
}

const deleteProductType = () => {
    const params = getUrlParams();
    const url = `product/${params.prodTypeId}/${params.periodId}/typedelete${stringifyUrlParams({...params, prodTypeId: undefined})}`;
    window.location.replace(url)
}

const deleteGrowingPeriod = () => {
    const params = getUrlParams();
    const url = `product/${params.periodId}/perioddelete${stringifyUrlParams({...params, periodId: undefined})}`;
    window.location.replace(url)
}

