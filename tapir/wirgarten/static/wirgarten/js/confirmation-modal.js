const modalElem = document.getElementById('confirmation-modal');
const modalTitleElem = document.getElementById('confirmationModalLabel');
const modalContentElem = document.getElementById('confirmationModalContent');
const modalConfirmButton = document.getElementById('confirmationModalConfirmButton');

const ConfirmationModal = {
    open: (title, content, confirmButtonLabel, confirmButtonType, handleConfirm = null, handleCancel = null) => {
        modalTitleElem.innerText = title;
        modalContentElem.innerHTML = content;

        if(!handleConfirm){
            modalConfirmButton.style.display='none'
        } else        {
            modalConfirmButton.innerText = confirmButtonLabel
                  if(!confirmButtonType){
                confirmButtonType = 'primary';
            }
            modalConfirmButton.className = "btn";
            modalConfirmButton.classList.add('btn-' + confirmButtonType);

            modalConfirmButton.addEventListener('click', () => {
                modalConfirmButton.disabled = true;
                handleConfirm();
                modal.hide()
            });
        }
        const modal = new bootstrap.Modal(modalElem);

        modal.show();
    }
}