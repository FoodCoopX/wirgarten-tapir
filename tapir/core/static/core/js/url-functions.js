const Tapir = {

    // takes an objects and converts it to a query string (e.g.: "?attr1=val1&attr2=val2")
    stringifyUrlParams: (params) =>
        '?' + Object.entries(params)
            .filter(p => p[0] && p[1])
            .map(p => `${p[0]}=${p[1]}` )
            .join('&'),

    // reads the query parameters into an object
    getUrlParams: () =>
        Object.fromEntries(
            window.location.search.substring(1)
            .split('&')
            .map(kv => kv.split('='))),

    // replaces the current query string with the new params object in the browser navbar
    replaceUrlParams: (params) =>
        history.replaceState({}, null, window.location.pathname + Tapir.stringifyUrlParams(params))

}