module.exports = {
    "env" : {
      "browser" : true,
      "es6" : true /** all es6 features except modules */
    },
    "plugins" : [
      "no-unsanitized",
      "prototype-pollution-security-rules",
      "no-wildcard-postmessage",
      "angularjs-security-rules",

    ],
    "rules" : {
  
      /** no-unsanitized rules**/
      "no-unsanitized/method": "error",
      "no-unsanitized/property": "error",
  
      /** prototype-pollution-security-rules rules**/
      "prototype-pollution-security-rules/detect-merge": 1,
      "prototype-pollution-security-rules/detect-merge-objects": 1,
      "prototype-pollution-security-rules/detect-merge-options": 1,
      "prototype-pollution-security-rules/detect-deep-extend": 1,
  
      /** no-wildcard-postmessage (NodeJS) rules**/
      "no-wildcard-postmessage/no-wildcard-postmessage": 1,
  
      /** angularjs-security-rules (Angular) rules**/
      "angularjs-security-rules/detect-angular-element-methods": 1,
      "angularjs-security-rules/detect-angular-open-redirect": 1,
      "angularjs-security-rules/detect-angular-orderBy-expressions": 1,
      "angularjs-security-rules/detect-angular-resource-loading": 1,
      "angularjs-security-rules/detect-angular-sce-disabled": 1,
      "angularjs-security-rules/detect-angular-scope-expressions": 1,
      "angularjs-security-rules/detect-angular-service-expressions": 1,
      "angularjs-security-rules/detect-angular-trustAs-methods": 1,
      "angularjs-security-rules/detect-angular-trustAsCss-method": 1,
      "angularjs-security-rules/detect-angular-trustAsHtml-method": 1,
      "angularjs-security-rules/detect-angular-sce-disabled": 1,
      "angularjs-security-rules/detect-angular-trustAsJs-method": 1,
      "angularjs-security-rules/detect-angular-trustAsResourceUrl-method": 1,
      "angularjs-security-rules/detect-angular-trustAsUrl-method": 1,
      "angularjs-security-rules/detect-third-party-angular-translate": 1,
    }
  };  