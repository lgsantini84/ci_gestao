/* static/js/app.js */
// Main application JavaScript file

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    })

    // Form submission loading state
    $('form').submit(function() {
        var submitBtn = $(this).find('button[type="submit"]')
        if (submitBtn.length) {
            submitBtn.prop('disabled', true)
                .html('<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processando...')
        }
    })

    // Auto-hide alerts
    setTimeout(function() {
        $('.alert:not(.alert-permanent)').alert('close')
    }, 5000)

    // Confirm delete dialogs
    $(document).on('click', '.confirm-delete', function(e) {
        if (!confirm('Tem certeza que deseja excluir este registro? Esta ação não pode ser desfeita.')) {
            e.preventDefault()
            return false
        }
    })

    // Format CPF input
    $('.cpf-input').inputmask('999.999.999-99')

    // Format phone input
    $('.phone-input').inputmask('(99) 99999-9999')

    // Format date input
    $('.date-input').inputmask('99/99/9999')

    // Format currency input
    $('.currency-input').inputmask('currency', {
        radixPoint: ',',
        groupSeparator: '.',
        allowMinus: false,
        prefix: 'R$ ',
        digits: 2,
        digitsOptional: false,
        rightAlign: false,
        unmaskAsNumber: true
    })

    // Format CNPJ input
    $('.cnpj-input').inputmask('99.999.999/9999-99')

    // Format NC input
    $('.nc-input').inputmask('9999999999')

    // Real-time validation
    $('.validate-email').on('blur', function() {
        var email = $(this).val()
        var regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (email && !regex.test(email)) {
            $(this).addClass('is-invalid')
            $(this).next('.invalid-feedback').text('Email inválido')
        } else {
            $(this).removeClass('is-invalid')
        }
    })

    // Toggle password visibility
    $(document).on('click', '.toggle-password', function() {
        var input = $(this).closest('.input-group').find('input')
        var type = input.attr('type') === 'password' ? 'text' : 'password'
        input.attr('type', type)
        $(this).find('i').toggleClass('fa-eye fa-eye-slash')
    })

    // File upload preview
    $('.file-upload').on('change', function() {
        var fileName = $(this).val().split('\\').pop()
        $(this).next('.custom-file-label').html(fileName)
    })

    // Character counter
    $('.char-counter').each(function() {
        var maxLength = $(this).data('maxlength')
        var counter = $('<small class="form-text text-muted char-counter-text"></small>')
        $(this).after(counter)
        
        $(this).on('input', function() {
            var length = $(this).val().length
            var remaining = maxLength - length
            counter.text(length + '/' + maxLength + ' caracteres')
            
            if (remaining < 0) {
                counter.addClass('text-danger')
            } else if (remaining < 10) {
                counter.addClass('text-warning')
            } else {
                counter.removeClass('text-danger text-warning')
            }
        }).trigger('input')
    })

    // Copy to clipboard
    $('.copy-to-clipboard').on('click', function() {
        var text = $(this).data('clipboard-text')
        var tempInput = $('<input>')
        $('body').append(tempInput)
        tempInput.val(text).select()
        document.execCommand('copy')
        tempInput.remove()
        
        // Show feedback
        var originalHtml = $(this).html()
        $(this).html('<i class="fas fa-check me-1"></i>Copiado!')
        setTimeout(() => {
            $(this).html(originalHtml)
        }, 2000)
    })

    // Auto-save forms
    var autoSaveTimeout
    $('.autosave').on('input', function() {
        clearTimeout(autoSaveTimeout)
        autoSaveTimeout = setTimeout(function() {
            $('.autosave').closest('form').submit()
        }, 2000)
    })

    // Load more button
    $('.load-more').on('click', function() {
        var button = $(this)
        var container = $(this).data('container')
        var url = $(this).data('url')
        var page = $(this).data('page') || 1
        
        button.prop('disabled', true)
            .html('<span class="spinner-border spinner-border-sm me-2"></span>Carregando...')
        
        $.get(url, { page: page + 1 }, function(data) {
            $(container).append(data.html)
            button.data('page', page + 1)
            
            if (!data.has_more) {
                button.hide()
            }
            
            button.prop('disabled', false)
                .html('<i class="fas fa-plus me-2"></i>Carregar Mais')
        })
    })

    // Refresh data
    $('.refresh-data').on('click', function() {
        var button = $(this)
        var target = $(this).data('target')
        
        button.prop('disabled', true)
            .find('i').addClass('fa-spin')
        
        $.get(window.location.href, function(data) {
            $(target).html($(data).find(target).html())
            button.prop('disabled', false)
                .find('i').removeClass('fa-spin')
        })
    })

    // Tab persistence
    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function(e) {
        localStorage.setItem('lastTab', $(e.target).attr('href'))
    })
    
    var lastTab = localStorage.getItem('lastTab')
    if (lastTab) {
        $('[href="' + lastTab + '"]').tab('show')
    }

    // Modal remote loading
    $('[data-bs-toggle="modal"][data-url]').on('click', function() {
        var url = $(this).data('url')
        var modal = $($(this).data('bs-target'))
        
        modal.find('.modal-content').load(url, function() {
            // Reinitialize any JS inside modal
            $(this).find('form').submit(function() {
                var submitBtn = $(this).find('button[type="submit"]')
                if (submitBtn.length) {
                    submitBtn.prop('disabled', true)
                        .html('<span class="spinner-border spinner-border-sm me-2"></span>Processando...')
                }
            })
        })
    })

    // Search with debounce
    var searchTimeout
    $('.live-search').on('input', function() {
        var input = $(this)
        var url = input.data('url')
        var target = input.data('target')
        var query = input.val()
        
        clearTimeout(searchTimeout)
        searchTimeout = setTimeout(function() {
            $.get(url, { q: query }, function(data) {
                $(target).html(data)
            })
        }, 500)
    })

    // Sortable tables
    $('.sortable th[data-sort]').on('click', function() {
        var table = $(this).closest('table')
        var sortField = $(this).data('sort')
        var sortDirection = $(this).data('direction') === 'asc' ? 'desc' : 'asc'
        
        // Reset all headers
        table.find('th').removeClass('sorting-asc sorting-desc')
        
        // Set current header
        $(this).addClass('sorting-' + sortDirection)
            .data('direction', sortDirection)
        
        // Sort table rows
        var rows = table.find('tbody tr').get()
        rows.sort(function(a, b) {
            var aVal = $(a).find('td[data-field="' + sortField + '"]').text()
            var bVal = $(b).find('td[data-field="' + sortField + '"]').text()
            
            if (sortDirection === 'asc') {
                return aVal.localeCompare(bVal)
            } else {
                return bVal.localeCompare(aVal)
            }
        })
        
        $.each(rows, function(index, row) {
            table.find('tbody').append(row)
        })
    })

    // Export data
    $('.export-btn').on('click', function() {
        var format = $(this).data('format')
        var url = $(this).data('url') + '?format=' + format
        
        window.location.href = url
    })

    // Print page
    $('.print-btn').on('click', function() {
        window.print()
    })

    // Fullscreen toggle
    $('.fullscreen-btn').on('click', function() {
        var elem = document.documentElement
        if (!document.fullscreenElement) {
            elem.requestFullscreen().catch(err => {
                console.error(`Error attempting to enable fullscreen: ${err.message}`)
            })
            $(this).find('i').removeClass('fa-expand').addClass('fa-compress')
        } else {
            document.exitFullscreen()
            $(this).find('i').removeClass('fa-compress').addClass('fa-expand')
        }
    })

    // Theme toggle (light/dark)
    var theme = localStorage.getItem('theme') || 'light'
    $('body').attr('data-theme', theme)
    
    $('.theme-toggle').on('click', function() {
        var currentTheme = $('body').attr('data-theme')
        var newTheme = currentTheme === 'light' ? 'dark' : 'light'
        
        $('body').attr('data-theme', newTheme)
        localStorage.setItem('theme', newTheme)
        
        $(this).find('i')
            .toggleClass('fa-moon fa-sun')
            .toggleClass('text-dark text-warning')
    })

    // Back to top button
    var backToTop = $('#back-to-top')
    
    $(window).scroll(function() {
        if ($(this).scrollTop() > 300) {
            backToTop.fadeIn()
        } else {
            backToTop.fadeOut()
        }
    })
    
    backToTop.on('click', function() {
        $('html, body').animate({ scrollTop: 0 }, 500)
        return false
    })

    // Initialize DataTables with custom options
    $.extend(true, $.fn.dataTable.defaults, {
        language: {
            url: "//cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json"
        },
        pageLength: 25,
        responsive: true,
        dom: "<'row'<'col-sm-12 col-md-6'l><'col-sm-12 col-md-6'f>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
        columnDefs: [
            { orderable: false, targets: 'no-sort' }
        ]
    })

    // Global error handler for AJAX requests
    $(document).ajaxError(function(event, jqxhr, settings, thrownError) {
        if (jqxhr.status === 401) {
            window.location.href = '/auth/login?next=' + encodeURIComponent(window.location.pathname)
        } else if (jqxhr.status === 403) {
            alert('Acesso negado. Você não tem permissão para esta ação.')
        } else if (jqxhr.status === 500) {
            alert('Erro interno do servidor. Por favor, tente novamente mais tarde.')
        }
    })

    // Initialize all DataTables
    $('.datatable').DataTable()

    // Initialize all Select2
    $('.select2').select2({
        theme: 'bootstrap-5',
        placeholder: "Selecione...",
        allowClear: true
    })

    // Initialize all input masks
    $('.input-mask').each(function() {
        var mask = $(this).data('mask')
        $(this).inputmask(mask)
    })

    console.log('Application initialized successfully')
})