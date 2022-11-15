const init = (pt_p_map_json, pe_pt_map_json) => {
    activateGrowingPeriodList(pe_pt_map_json)
    activateProductTypeList(pt_p_map_json)
    activateProductList();
    manageButtons();
    activateDetails();

    const frame = document.getElementById("productModalContainer");

    // Adjusting the iframe height onload event
    frame.onload = () => {
        console.log(frame.style)
        frame.style.height = '0px' // for some reason this is necessary
        frame.style.height = frame.contentWindow.document.body.scrollHeight + 'px';
        frame.style.width = frame.contentWindow.document.body.scrollWidth+'px';
    }
}


// page logic
const activateDetails = () => {
    const params = Tapir.getUrlParams();
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
    const params = Tapir.getUrlParams();
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
    const params = Tapir.getUrlParams();
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
    const params = Tapir.getUrlParams();
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
    const params = Tapir.getUrlParams();
    manageGrowingPeriodDependentButtons(params);
    manageProductTypeDependentButtons(params);
    manageProductDependentButtons(params);
}

// dynamic Forms
const AddModal = (url, title) => {
    const xframe = document.getElementById("productModalContainer")
    xframe.src = url;

    document.getElementById("modalLabel").innerHTML = title;
}

const getProductTypeEditForm = () => {
    const params = Tapir.getUrlParams();
    if (params.prodTypeId) {
        const url = `/wirgarten/product/${params.prodTypeId}/${params.periodId}/typeedit${Tapir.stringifyUrlParams(params)}`;
        AddModal(url, "Produkt Typ editieren");
    }
}

const getProductTypeAddForm = () => {
    const params = Tapir.getUrlParams();
    const url = `/wirgarten/product/${params.periodId}/typeadd${Tapir.stringifyUrlParams(params)}`;
    AddModal(url, "Neuen Produkt Typ hinzufügen");
}

const getProductEditForm = () => {
    const params = Tapir.getUrlParams();
    if (params.prodId) {
        const url = `/wirgarten/product/${params.prodId}/edit${Tapir.stringifyUrlParams(params)}`;
        AddModal(url, "Produkt editieren");
    }
}

const getProductAddForm = () => {
    const params = Tapir.getUrlParams();
    const url = `/wirgarten/product/${params.prodTypeId}/add${Tapir.stringifyUrlParams(params)}`;
    AddModal(url, "Neues Produkt hinzufügen");
}

const getGrowingPeriodAddForm = () => {
    const params = Tapir.getUrlParams();
    const url = `/wirgarten/product/periodadd${Tapir.stringifyUrlParams(params)}`;
    const title = `Neue Anbauperiode anlegen. Ohne Produkte
     Es wird empfohlen stattdessen die Copy Funktion auf die letzte Periode Anzuwenden,
     damit Produkte und weitere Einstellungen übernommen werden. Diese sind noch nachträglich editierbar.`;
    AddModal(url, title);
}

const getGrowingPeriodCopyForm = () => {
    const params = Tapir.getUrlParams();
    const url = `/wirgarten/product/${params.periodId}/periodcopy${Tapir.stringifyUrlParams(params)}`;
    AddModal(url, "Neue Anbauperiode anlegen. Produkte werden übernommen.");
}

// actions
const select_period = (periodId, pe_pt_map_json) => {
    const params = Tapir.getUrlParams();
    if(params.periodId !== periodId) {
        params.prodTypeId = null;
        params.prodId = null;
    }
    params.periodId = periodId;
    Tapir.replaceUrlParams(params);
    activateGrowingPeriodList(pe_pt_map_json);
    activateDetails();
    manageButtons();
}

const select_product_type = (productTypeId, pt_p_map_json) => {
    const params = Tapir.getUrlParams();
    if(params.prodTypeId !== productTypeId) {
        params.prodId = null;
    }
    params.prodTypeId = productTypeId;
    Tapir.replaceUrlParams(params);
    activateProductTypeList(pt_p_map_json);
    activateDetails();
    manageButtons();
}

const select_product = (productId) => {
    const params = Tapir.getUrlParams();
    params.prodId = productId;
    Tapir.replaceUrlParams(params);
    activateProductList();
    activateDetails();
    manageButtons();
}

const deleteProduct = () => {
    const params = Tapir.getUrlParams();
    const url = `product/${params.prodId}/delete${Tapir.stringifyUrlParams({...params, prodId: undefined})}`;
    window.location.replace(url)
}

const deleteProductType = () => {
    const params = Tapir.getUrlParams();
    const url = `product/${params.prodTypeId}/${params.periodId}/typedelete${Tapir.stringifyUrlParams({...params, prodTypeId: undefined})}`;
    window.location.replace(url)
}

const deleteGrowingPeriod = () => {
    const params = Tapir.getUrlParams();
    const url = `product/${params.periodId}/perioddelete${Tapir.stringifyUrlParams({...params, periodId: undefined})}`;
    window.location.replace(url)
}

