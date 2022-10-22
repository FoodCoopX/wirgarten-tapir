const search = document.getElementById('search-input')
search.addEventListener('input', (event) => {

    for(const param of document.getElementsByClassName('single-parameter')){
        if(!param.outerText.toLowerCase().includes(event.target.value.toLowerCase())){
            param.style.display = 'none'
        } else {
            param.style.display = 'block'
        }
    }

    for(const category of document.getElementsByClassName('parameter-category')){
        if(Array.from(category.getElementsByClassName('single-parameter')).filter(it => it.style.display != 'none').length === 0){
            category.style.display = 'none'
        } else {
            category.style.display = 'block'
        }
    }
})