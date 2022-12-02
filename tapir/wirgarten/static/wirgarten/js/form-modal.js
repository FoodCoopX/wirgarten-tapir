const frame = document.getElementById("content-frame");
const loadingIndicator = document.getElementById("modal-loading-indicator");

const showLoadingIndicator = (show) => {
    loadingIndicator.style.display = show ? 'flex' : 'none';
}

const setFrameSize = () => {
    const form = frame.contentWindow.document.getElementsByTagName("form")
    if(form.length > 0){
        const newHeight = form[0].getBoundingClientRect().height
        frame.style.minHeight = frame.style.maxHeight = newHeight + 'px';
        frame.style.width = frame.contentWindow.document.body.scrollWidth+'px';
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
        load: (url, title) => {
            showLoadingIndicator(true);

            document.getElementById("modalLabel").innerText=title;

            frame.style.minHeight = frame.style.maxHeight = "0px";
            frame.src=url

            // Adjusting the iframe height onload event
            frame.onload = () => {
                setFrameSize();
                showLoadingIndicator(false);
            }

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
        ["modal-close", () => FormModal.close()],
        ["modal-save-successful", (data) => data.url && data.url != 'None' ? window.location.replace(data.url) : FormModal.close()],
        ["modal-loading-spinner", () => {
            frame.style.minHeight = frame.style.maxHeight = "0px";
            showLoadingIndicator(true)
        }],
        ["modal-content-resized", () => setFrameSize()]
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