document.querySelectorAll('form[data-static-preview=true]').forEach(function(form){
  form.addEventListener('submit',function(event){
    event.preventDefault();
    var message=form.querySelector('.github-preview-message');
    if(!message){message=document.createElement('p');message.className='github-preview-message';message.setAttribute('role','status');form.appendChild(message);}
    message.textContent='このサイトは確認用のため、フォームから送信できません。';
    message.scrollIntoView({behavior:'smooth',block:'center'});
  });
});
