"""
Django settings for core project.

Generated by 'django-admin startproject' using Django 3.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""
from datetime import timedelta
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


'''
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # Add your frontend domain here
    'https://banbury-405719.ue.r.appspot.com',
    '*'
    # Add other allowed origins as needed
]
'''
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'fxfwao!b&53)8l$t3nc(+)9^63t%b09f_dn@jx6e_(ghhkbgh5'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Change this to your production URL for deployment
ALLOWED_HOSTS = ['*']

# CSRF_TRUSTED_ORIGINS = ['https://website2-v3xlkt54dq-uc.a.run.app']
# CSRF_TRUSTED_ORIGINS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',  # Make sure this line is present
    # 'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'apps.authentication',
    'apps.devices',
    'apps.files',
    'apps.predictions',
    'apps.profiles',
    'apps.sessions',
    'apps.settings',
    'apps.users',
    'apps.tasks',
    'rest_framework',
    'corsheaders',
    'rest_framework.authtoken',
    'drf_spectacular',
    'websocket',
]


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Or other authentication class
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    'SLIDING_TOKEN_LIFETIME': timedelta(days=1),
    'SLIDING_TOKEN_REFRESH_AFTER_LIFETIME': timedelta(days=14),
    'SLIDING_TOKEN_REFRESH_SLIDING_LIFETIME': timedelta(days=14),
    'SLIDING_TOKEN_SLIDING_LIFETIME': timedelta(days=14),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['apps/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages'

            ],
        },
    },
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'colored': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s%(levelname)s %(asctime)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}



WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.urls.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        # 'BACKEND': 'channels_redis.core.InMemoryChannelLayer',
        'CONFIG': {
            # "hosts": [('0.0.0.0', 8080)],
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

CORS_ALLOW_ALL_ORIGINS = True

SPECTACULAR_SETTINGS = {
    'TITLE': 'Banbury API',
    'DESCRIPTION': 'Banbury API',
    'VERSION': '1.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    
    # UI Settings
    'SWAGGER_UI_SETTINGS': {
        'displayOperationId': True,
        'theme': 'dark',
        'deepLinking': True,
        'persistAuthorization': True,
        'defaultModelsExpandDepth': 3,
        'defaultModelExpandDepth': 3,
        'defaultModelRendering': 'model',
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'tryItOutEnabled': True,
        'syntaxHighlight': {
            'theme': 'monokai'
        },
        'customCss': '''
            /* Dark mode base colors */
            body { background-color: #111827; }
            .swagger-ui { background-color: #111827; color: #e5e7eb; }
            
            /* Header and navigation */
            .swagger-ui .topbar { background-color: #1f2937; }
            .swagger-ui .info .title { color: #60a5fa; }
            .swagger-ui .info { color: #e5e7eb; }
            .swagger-ui .scheme-container { background-color: #1f2937; box-shadow: none; }
            
            /* Operation blocks */
            .swagger-ui .opblock-tag { color: #f3f4f6; background: #111827; }
            .swagger-ui .opblock { background: #1f2937; border: 1px solid #374151; }
            .swagger-ui .opblock .opblock-summary { border-bottom: 1px solid #374151; }
            .swagger-ui .opblock .opblock-summary-method { background: #3b82f6; }
            .swagger-ui .opblock .opblock-summary-path { color: #e5e7eb; }
            .swagger-ui .opblock .opblock-summary-description { color: #9ca3af; }
            
            /* Models and Schemas */
            .swagger-ui .model { color: #e5e7eb; }
            .swagger-ui .model-title { color: #e5e7eb; }
            .swagger-ui section.models { border: 1px solid #374151; background: #1f2937; }
            .swagger-ui section.models.is-open h4 { border-bottom: 1px solid #374151; }
            
            /* Tables and Properties */
            .swagger-ui .table-container { background-color: #1f2937; }
            .swagger-ui table thead tr td, 
            .swagger-ui table thead tr th { color: #e5e7eb; }
            .swagger-ui .parameters-col_description { color: #e5e7eb; }
            .swagger-ui .parameter__name { color: #60a5fa; }
            .swagger-ui .parameter__type { color: #9ca3af; }
            
            /* Response section */
            .swagger-ui .responses-inner { background: #1f2937; }
            .swagger-ui .response-col_status { color: #60a5fa; }
            .swagger-ui .response-col_description { color: #e5e7eb; }
            
            /* Inputs and Buttons */
            .swagger-ui input[type=text], 
            .swagger-ui input[type=password] { 
                background-color: #374151; 
                color: #e5e7eb; 
                border: 1px solid #4b5563; 
            }
            .swagger-ui select {
                background-color: #374151;
                color: #e5e7eb;
                border: 1px solid #4b5563;
            }
            .swagger-ui .btn { background-color: #3b82f6; color: #fff; }
            
            /* Authorization */
            .swagger-ui .dialog-ux .modal-ux { background: #1f2937; }
            .swagger-ui .dialog-ux .modal-ux-header { background: #111827; }
            .swagger-ui .dialog-ux .modal-ux-content { background: #1f2937; }
            
            /* Code samples */
            .swagger-ui .highlight-code { background-color: #111827; }
        '''
    },
    
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'hideHostname': False,
        'expandResponses': '200,201',
        'jsonSampleExpandLevel': 3,
        'hideLoading': False,
        'nativeScrollbars': False,
        'pathInMiddlePanel': False,
        'requiredPropsFirst': True,
        'sortPropsAlphabetically': True,
    },
}


