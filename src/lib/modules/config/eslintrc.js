module.exports = {
    "env" : {
      "browser" : true,
      "es6" : true /** all es6 features except modules */
    },
    "plugins" : [
      "no-unsanitized",
      "prototype-pollution-security-rules",
      "no-wildcard-postmessage"
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
      "no-wildcard-postmessage/no-wildcard-postmessage": 1
    }
  };  