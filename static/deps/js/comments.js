const commentForm = document.forms.commentForm;
const commentFormContent = commentForm.content;
const commentFormParentInput = commentForm.parent;
const commentFormSubmit = commentForm.commentSubmit;
const commentPostId = commentForm.getAttribute('data-post-id');
let lastCommentTime = parseInt(localStorage.getItem('lastCommentTime')) || 0; // Получаем время из localStorage или 0
let alertShown = false; // Переменная для отслеживания, было ли показано сообщение

commentForm.addEventListener('submit', createComment);
replyUser();

function replyUser() {
    document.querySelectorAll('.btn-reply').forEach(e => {
        e.addEventListener('click', replyComment);
    });
}

function replyComment() {
    const commentUsername = this.getAttribute('data-comment-username');
    const commentMessageId = this.getAttribute('data-comment-id');
    commentFormContent.value = `${commentUsername}, `;
    commentFormParentInput.value = commentMessageId;
}

async function createComment(event) {
    event.preventDefault();

    const currentTime = Date.now();
    const timeLimit = 60 * 1000; // Ограничение в одну минуту (в миллисекундах)

    if (currentTime - lastCommentTime < timeLimit) {
        // Показываем сообщение об ошибке в шаблоне
        document.getElementById('commentError').classList.remove('d-none');
        setTimeout(() => {
            document.getElementById('commentError').classList.add('d-none');
        }, 5000); // Скрываем сообщение через 5 секунд
        return;
    }

    lastCommentTime = currentTime;
    localStorage.setItem('lastCommentTime', lastCommentTime);
    commentFormSubmit.disabled = true;
    commentFormSubmit.innerText = "Ожидаем ответа сервера";

    try {
        const response = await fetch(`/post/${commentPostId}/comments/create/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: new FormData(commentForm),
        });

        const comment = await response.json();

        // Создаем элемент списка комментариев
        const li = document.createElement('li');
        li.className = 'card border-0';

        // Добавляем содержимое комментария
        li.innerHTML = ` <div class="row"> <div class="col-md-2"> <img src="${comment.photo}" style="width: 100px; height: 100px; object-fit: cover; border-radius: 50%;"> </div> <div class="col-md-10"> <div class="card-body"> <h6 class="card-title"><p>${comment.author}</p></h6> <p class="card-text">${comment.content}</p> <a class="btn btn-sm btn-dark btn-reply" href="#commentForm" data-comment-id="${comment.id}" data-comment-username="${comment.author}">Ответить</a> <hr /> <time>${comment.time_create}</time> </div> </div> </div> `;

        // Вставляем новый комментарий в нужное место
        if (comment.is_child) {
            const parentThread = document.querySelector(`#comment-thread-${comment.parent_id}`);
            parentThread.appendChild(li);
        } else {
            const commentsContainer = document.querySelector('.nested-comments');
            commentsContainer.appendChild(li);
        }

        commentForm.reset();
        commentFormSubmit.disabled = false;
        commentFormSubmit.innerText = "Добавить комментарий";
        commentFormParentInput.value = null;
        replyUser();
    } catch (error) {
        console.log(error);
    }
}