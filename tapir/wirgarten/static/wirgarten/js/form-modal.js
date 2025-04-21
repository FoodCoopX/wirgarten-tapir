const frame = document.getElementById("content-frame");
const loadingIndicator = document.getElementById("modal-loading-indicator");

const showLoadingIndicator = (show) => {
    loadingIndicator.style.display = show ? 'flex' : 'none';
}

const setFrameSize = () => {
    const form = frame.contentWindow.document.getElementsByTagName("form")
    if(form.length > 0) {
       if(form[0].offsetHeight && form[0].offsetWidth){
           frame.style.minHeight = frame.style.maxHeight = form[0].offsetHeight + 'px';
           frame.style.minWidth = frame.style.maxWidth = form[0].offsetWidth + 'px';
       } else {
            setTimeout(setFrameSize, 50);
       }
    }
}

const eventMethod = window.addEventListener
            ? "addEventListener"
            : "attachEvent";
const eventer = window[eventMethod];
const messageEvent = eventMethod === "attachEvent"
        ? "onmessage"
        : "message";

 const FormModal = {
        load: (url, title, info=undefined, infoType="info") => {
            showLoadingIndicator(true);

            document.getElementById("modalLabel").innerText=title;
            const modalInfo = document.getElementById("modalInfo")
            const modalInfoContent = document.getElementById("modalInfoContent")

            modalInfo.style.display="none";
            modalInfoContent.innerText="";

            if (info !== undefined && info.length > 0) {
                modalInfo.style.display="block";

                if(modalInfoContent){
                    modalInfoContent.innerText=info;

                    for(clazz of modalInfoContent.classList){
                        if(clazz.startsWith("alert-")){
                            modalInfoContent.classList.remove(clazz);
                        }
                    }
                    modalInfoContent.classList.add("alert-" + infoType);
                }
            }

            frame.style.maxHeight = frame.style.minHeight = '0px';
            frame.src=url

            // Adjusting the iframe height onload event
            frame.onload = () => {
                const contentDocument = frame.contentDocument || frame.contentWindow.document;

                // Check if the document body contains any form or expected content.
                const formExists = contentDocument.querySelector('.form-fields') !== null;
                if (!formExists) {
                    // If no form or expected content, display the error message.
                    modalInfo.style.display = "block";
                    modalInfo.style.marginBottom = "1em";
                    modalInfoContent.className = "alert alert-danger"; // Reset classes and add alert-danger.
                    modalInfoContent.innerText = "Ein Fehler ist aufgetreten. Bitte versuche es später erneut oder kontaktiere den Admin!";
                    frame.style.display = "none";
                } else {
                    frame.style.display = "block";
                    modalInfo.style.display = "none"
                    setFrameSize(); // If form exists, adjust the size as needed.
                }

                showLoadingIndicator(false);
            };

            const modal = new bootstrap.Modal(document.getElementById('form-modal'))
            modal.show()
        },

        close: () => {
            const modalInstance = bootstrap.Modal.getInstance(document.getElementById('form-modal'));
            modalInstance.hide();
        },

        addCallback: (callback) => {
            eventer(messageEvent, callback);
        }
    }

MSG_HANDLERS = [
        ["modal-close", FormModal.close],
        ["modal-save-successful", (data) => data.url && data.url != 'None' ? window.location.replace(data.url) : FormModal.close()],
        ["modal-loading-spinner", () => {
            frame.style.minHeight = frame.style.maxHeight = '0px';
            showLoadingIndicator(true)
        }],
        ["modal-content-resized", setFrameSize]
    ]

const initMessageHandlers = () => {
    const handleMessage = (event, msgType, handler) => {
        if(event.data.type === msgType){
            handler(event.data.data);
        }
    }

    eventer(messageEvent, (e) => {
       MSG_HANDLERS.forEach(([msgType, handler]) => handleMessage(event, msgType, handler))
    });
}

initMessageHandlers();