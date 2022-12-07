const modalElem = document.getElementById('confirmation-modal');
const modalTitleElem = document.getElementById('confirmationModalLabel');
const modalContentElem = document.getElementById('confirmationModalContent');
const modalConfirmButton = document.getElementById('confirmationModalConfirmButton');

const ConfirmationModal = {
    open: (title, content, confirmButtonLabel, confirmButtonType, handleConfirm, handleCancel = null) => {
        modalTitleElem.innerText = title;
        modalContentElem.innerHTML = content;

        modalConfirmButton.innerText = confirmButtonLabel

        if(!confirmButtonType){
            confirmButtonType = 'primary';
        }
        modalConfirmButton.className = "btn";
        modalConfirmButton.classList.add('btn-' + confirmButtonType);

        const modal = new bootstrap.Modal(modalElem);

        modalConfirmButton.addEventListener('click', () => {
            handleConfirm();
            modal.hide()
        });

        modal.show();
    }
}